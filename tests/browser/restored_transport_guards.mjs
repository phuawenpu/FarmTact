import {spawnSync} from 'node:child_process';
import {writeFile} from 'node:fs/promises';
const cases=[
 ['valid V20 target',{EXPECTED_EDITION:'v20',STAGED_CONTAINER:'v20',STAGED_PORT:'8100'},true],
 ['wrong edition container',{EXPECTED_EDITION:'v20',STAGED_CONTAINER:'v19',STAGED_PORT:'8100'},false],
 ['wrong candidate port',{EXPECTED_EDITION:'v20',STAGED_CONTAINER:'v20',STAGED_PORT:'8099'},false],
 ['unbounded port',{EXPECTED_EDITION:'v20',STAGED_CONTAINER:'v20',STAGED_PORT:'80'},false],
 ['non-numeric port',{EXPECTED_EDITION:'v20',STAGED_CONTAINER:'v20',STAGED_PORT:'8100@evil.invalid'},false],
 ['edition path injection',{EXPECTED_EDITION:'v20/../v19',STAGED_CONTAINER:'v20',STAGED_PORT:'8100'},false],
 ['unapproved future edition',{EXPECTED_EDITION:'v22',STAGED_CONTAINER:'v22',STAGED_PORT:'8102'},false],
];
const checks=[];
for(const [name,overrides,expected] of cases){
 const result=spawnSync(process.execPath,['--input-type=module','-e',"await import('./tests/browser/restored_staged_transport.mjs')"],{env:{...process.env,...overrides},encoding:'utf8'});
 checks.push({name,pass:(result.status===0)===expected});
}
const {stagedTransport}=await import('./restored_staged_transport.mjs');
for(const source of ['', '123abc', '../source', 'g'.repeat(40)]){
 let rejected=false;try{await stagedTransport(source)}catch(e){rejected=String(e).includes('Full staged source identity required')}
 checks.push({name:`reject malformed source length ${source.length} before SSH`,pass:rejected});
}
const report={status:checks.every(c=>c.pass)?'PASS':'FAIL',checks,network_requests:0};
await writeFile('/tmp/restored-transport-guards.json',JSON.stringify(report,null,2)+'\n');console.log(report.status, checks.length);if(report.status!=='PASS')process.exitCode=1;
