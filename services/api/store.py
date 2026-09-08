"""Tenant-scoped durable snapshots/jobs/events. PostgreSQL in service, SQLite only explicit tests."""
import os, secrets, hashlib
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime,timezone
from pathlib import Path
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, JSON, ForeignKey, ForeignKeyConstraint, UniqueConstraint, select, update
from sqlalchemy.pool import StaticPool

metadata=MetaData()
tenants=Table('tenants',metadata,Column('id',String,primary_key=True),Column('session_hash',String,unique=True,nullable=False),Column('created_at',String,nullable=False))
farms=Table('farm_versions',metadata,Column('id',String,primary_key=True),Column('tenant_id',String,ForeignKey('tenants.id'),nullable=False),Column('version',Integer,nullable=False),Column('input_hash',String,nullable=False),Column('payload',JSON,nullable=False),UniqueConstraint('tenant_id','version'))
runs=Table('planning_runs',metadata,Column('id',String,primary_key=True),Column('tenant_id',String,ForeignKey('tenants.id'),nullable=False),Column('idempotency_key',String,nullable=False),Column('request_hash',String,nullable=False),Column('status',String,nullable=False),Column('payload',JSON,nullable=False),UniqueConstraint('tenant_id','idempotency_key'),UniqueConstraint('id','tenant_id',name='run_tenant_identity'))
events=Table('run_events',metadata,Column('id',Integer,primary_key=True),Column('run_id',String,ForeignKey('planning_runs.id'),nullable=False),Column('tenant_id',String,ForeignKey('tenants.id'),nullable=False),Column('sequence',Integer,nullable=False),Column('payload',JSON,nullable=False),UniqueConstraint('run_id','sequence'),ForeignKeyConstraint(['run_id','tenant_id'],['planning_runs.id','planning_runs.tenant_id'],name='event_run_tenant_fk'))
budget=Table('inference_budget',metadata,Column('id',String,primary_key=True),Column('reserved_calls',Integer,nullable=False))

def now(): return datetime.now(timezone.utc).isoformat()
class Store:
    def __init__(self,url=None):
        url=url or os.environ.get('FARMTACT_DATABASE_URL','postgresql+psycopg://sprite@/farmtact?host=/tmp/farmtact-pg')
        opts={}
        if url=='sqlite://': opts=dict(connect_args={'check_same_thread':False},poolclass=StaticPool)
        self.engine=create_engine(url,**opts)
        self._transaction=ContextVar("farmtact_transaction",default=None)
        if url.startswith('sqlite'):
            from sqlalchemy import event
            @event.listens_for(self.engine,'connect')
            def fk(dbapi,record): dbapi.execute('PRAGMA foreign_keys=ON')
        metadata.create_all(self.engine)
        if self.engine.dialect.name=='postgresql':
            from sqlalchemy import inspect,text
            inspector=inspect(self.engine)
            with self.engine.begin() as c:
                if 'run_tenant_identity' not in {x['name'] for x in inspector.get_unique_constraints('planning_runs')}:
                    c.execute(text('ALTER TABLE planning_runs ADD CONSTRAINT run_tenant_identity UNIQUE (id, tenant_id)'))
                if 'event_run_tenant_fk' not in {x['name'] for x in inspector.get_foreign_keys('run_events')}:
                    c.execute(text('ALTER TABLE run_events ADD CONSTRAINT event_run_tenant_fk FOREIGN KEY (run_id, tenant_id) REFERENCES planning_runs (id, tenant_id)'))
    @contextmanager
    def connection(self,write=False):
        current=self._transaction.get()
        if current is not None:
            yield current
        else:
            with (self.engine.begin() if write else self.engine.connect()) as c:yield c
    @contextmanager
    def transaction(self,tenant=None):
        with self.engine.begin() as c:
            token=self._transaction.set(c)
            try:
                if tenant:c.execute(select(tenants.c.id).where(tenants.c.id==tenant).with_for_update())
                yield c
            finally:self._transaction.reset(token)
    def new_session(self):
        token=secrets.token_urlsafe(32); tenant=secrets.token_hex(16)
        with self.connection(write=True) as c:c.execute(tenants.insert().values(id=tenant,session_hash=hashlib.sha256(token.encode()).hexdigest(),created_at=now()))
        return tenant,token
    def authenticate(self,token):
        if not token or len(token)>200:return None
        with self.connection() as c:return c.execute(select(tenants.c.id).where(tenants.c.session_hash==hashlib.sha256(token.encode()).hexdigest())).scalar_one_or_none()
    def latest_farm(self,tenant):
        with self.connection() as c:return c.execute(select(farms.c.payload).where(farms.c.tenant_id==tenant).order_by(farms.c.version.desc()).limit(1)).scalar_one_or_none()
    def save_farm(self,tenant,payload):
        from packages.contracts import content_hash
        with self.connection(write=True) as c:
            # Serialize version allocation against this tenant row.
            c.execute(select(tenants.c.id).where(tenants.c.id==tenant).with_for_update())
            current=c.execute(select(farms.c.version).where(farms.c.tenant_id==tenant).order_by(farms.c.version.desc()).limit(1)).scalar_one_or_none() or 0
            payload=dict(payload,version=current+1)
            c.execute(farms.insert().values(id=secrets.token_hex(16),tenant_id=tenant,version=current+1,input_hash=content_hash(payload),payload=payload))
        return payload
    def get_run(self,tenant,id):
        with self.connection() as c:return c.execute(select(runs.c.payload).where(runs.c.id==id,runs.c.tenant_id==tenant)).scalar_one_or_none()
    def latest_run(self,tenant):
        with self.connection() as c:
            rows=c.execute(select(runs.c.payload).where(runs.c.tenant_id==tenant)).scalars().all()
        return max(rows,key=lambda r:r['created_at']) if rows else None
    def create_run(self,tenant,key,request_hash,payload):
        with self.connection(write=True) as c:
            c.execute(select(tenants.c.id).where(tenants.c.id==tenant).with_for_update())
            old=c.execute(select(runs).where(runs.c.tenant_id==tenant,runs.c.idempotency_key==key)).mappings().first()
            if old:
                if old['request_hash']!=request_hash:raise ValueError('Idempotency key reused with changed inputs')
                return old['payload'],False
            active=c.execute(select(runs.c.id).where(runs.c.tenant_id==tenant,runs.c.status.in_(['CREATED','RUNNING']))).first()
            if active:raise ValueError('A planning mission is already running')
            c.execute(runs.insert().values(id=payload['id'],tenant_id=tenant,idempotency_key=key,request_hash=request_hash,status=payload['status'],payload=payload))
        return payload,True
    def save_run(self,tenant,payload):
        with self.connection(write=True) as c:c.execute(update(runs).where(runs.c.id==payload['id'],runs.c.tenant_id==tenant).values(payload=payload,status=payload['status']))
    def append_event(self,tenant,id,type,body):
        with self.connection(write=True) as c:
            owner=c.execute(select(runs.c.id).where(runs.c.id==id,runs.c.tenant_id==tenant).with_for_update()).scalar_one_or_none()
            if owner is None:raise ValueError('Mission not owned by tenant')
            seq=(c.execute(select(events.c.sequence).where(events.c.run_id==id,events.c.tenant_id==tenant).order_by(events.c.sequence.desc()).limit(1)).scalar_one_or_none() or 0)+1
            event=dict(run_id=id,sequence=seq,occurred_at=now(),event_type=type,schema_version='1.0',body=body)
            c.execute(events.insert().values(run_id=id,tenant_id=tenant,sequence=seq,payload=event))
        return event
    def get_events(self,tenant,id,after=0):
        with self.connection() as c:return list(c.execute(select(events.c.payload).where(events.c.tenant_id==tenant,events.c.run_id==id,events.c.sequence>after).order_by(events.c.sequence)).scalars())
    def pending(self):
        with self.connection() as c:return c.execute(select(runs.c.tenant_id,runs.c.id).where(runs.c.status=='CREATED')).all()
    def claim(self,tenant,id):
        with self.connection(write=True) as c:return c.execute(update(runs).where(runs.c.id==id,runs.c.tenant_id==tenant,runs.c.status=='CREATED').values(status='RUNNING')).rowcount==1
    def interrupt_abandoned(self):
        with self.connection(write=True) as c:
            rows=c.execute(select(runs).where(runs.c.status=='RUNNING')).mappings().all()
            for row in rows:
                p=row['payload'];p['status']='FAILED';p['warnings'].append('Worker restarted during execution; inference was not repeated. Start a new mission explicitly.')
                c.execute(update(runs).where(runs.c.id==row['id']).values(status='FAILED',payload=p))
    def release_unused_calls(self,count):
        if not isinstance(count,int) or count<0:raise ValueError('Nonnegative unused reservation required')
        if count==0:return
        day=now()[:10]
        with self.connection(write=True) as c:
            result=c.execute(update(budget).where(budget.c.id==day,budget.c.reserved_calls>=count).values(reserved_calls=budget.c.reserved_calls-count))
            if result.rowcount!=1:raise ValueError('Invalid budget reconciliation')
    def reserve_calls(self,count,limit=48):
        if not isinstance(count,int) or isinstance(count,bool) or count<=0:raise ValueError("Positive request reservation required")
        # One global daily reservation prevents public demo sessions multiplying paid requests.
        day=now()[:10]
        from sqlalchemy.exc import IntegrityError
        try:
            with self.connection(write=True) as c:c.execute(budget.insert().values(id=day,reserved_calls=0))
        except IntegrityError:pass
        with self.connection(write=True) as c:
            result=c.execute(update(budget).where(budget.c.id==day,budget.c.reserved_calls+count<=limit).values(reserved_calls=budget.c.reserved_calls+count))
        return result.rowcount==1
