import {spawnSync} from 'node:child_process';
import {writeFile} from 'node:fs/promises';
const cases=[
 ['valid V17 target',{EXPECTED_EDITION:'v17',STAGED_CONTAINER:'v17',STAGED_PORT:'8097'},true],
 ['wrong edition container',{EXPECTED_EDITION:'v17',STAGED_CONTAINER:'v16',STAGED_PORT:'8097'},false],
 ['wrong candidate port',{EXPECTED_EDITION:'v17',STAGED_CONTAINER:'v17',STAGED_PORT:'8096'},false],
 ['unbounded port',{EXPECTED_EDITION:'v17',STAGED_CONTAINER:'v17',STAGED_PORT:'80'},false],
 ['non-numeric port',{EXPECTED_EDITION:'v17',STAGED_CONTAINER:'v17',STAGED_PORT:'8097@evil.invalid'},false],
 ['edition path injection',{EXPECTED_EDITION:'v17/../v16',STAGED_CONTAINER:'v17',STAGED_PORT:'8097'},false],
 ['unapproved future edition',{EXPECTED_EDITION:'v18',STAGED_CONTAINER:'v18',STAGED_PORT:'8098'},false],
];
const checks=[];
for(const [name,overrides,expected] of cases){
 const result=spawnSync(process.execPath,['--input-type=module','-e',"await import('./tests/browser/v17_staged_transport.mjs')"],{env:{...process.env,...overrides},encoding:'utf8'});
 checks.push({name,pass:(result.status===0)===expected});
}
const {stagedTransport}=await import('./v17_staged_transport.mjs');
for(const source of ['', '123abc', '../source', 'g'.repeat(40)]){
 let rejected=false;try{await stagedTransport(source)}catch(e){rejected=String(e).includes('Full staged source identity required')}
 checks.push({name:`reject malformed source length ${source.length} before SSH`,pass:rejected});
}
const report={status:checks.every(c=>c.pass)?'PASS':'FAIL',checks,network_requests:0};
await writeFile('reports/v17/transport-guards.json',JSON.stringify(report,null,2)+'\n');console.log(report.status, checks.length);if(report.status!=='PASS')process.exitCode=1;
