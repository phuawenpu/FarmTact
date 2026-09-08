import subprocess,sys
from pathlib import Path

def test_actual_process_socket_policy_blocks_alternate_egress():
    script='''
from services.api.egress import install
import socket,httpx
install()
for host,port in [('127.0.0.1',12345),('169.254.169.254',80),('1.1.1.1',443)]:
    try:socket.socket().connect((host,port))
    except PermissionError:pass
    else:raise AssertionError('unexpected outbound connection')
try:httpx.get('https://example.com',trust_env=False,timeout=1)
except (PermissionError,httpx.ConnectError):pass
else:raise AssertionError('alternate HTTPS destination connected')
print('Outbound negative probes passed')
'''
    result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
    assert 'negative probes passed' in result.stdout


def test_only_explicit_database_destination_can_connect():
    script = """
import os,socket
from services.api.egress import install
server=socket.socket(); server.bind(('127.0.0.1',0)); server.listen(1)
port=server.getsockname()[1]
os.environ['FARMTACT_DATABASE_URL']=f'postgresql+psycopg://demo@localhost:{port}/demo'
install()
client=socket.create_connection(('localhost',port), timeout=1)
peer,_=server.accept(); peer.close(); client.close(); server.close()
try:socket.socket().connect(('127.0.0.1',port+1))
except PermissionError:pass
else:raise AssertionError('database port policy bypass')
print('Configured database connection passed')
"""
    result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,timeout=10)
    assert result.returncode == 0, result.stderr
