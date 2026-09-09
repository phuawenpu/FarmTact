import assert from 'node:assert/strict'
import { runSoundOutcome, scenarioSoundOutcome } from '../../apps/web/src/lib/game.ts'

const run=(status,shortfall=0)=>({id:'run',status,input_version:'fixture',created_at:'fixture',execution_mode:'test',data_mode:'synthetic',strategies:[{id:'balanced',name:'Balanced',metrics:{shortfall_kg:shortfall}}],claims:[],events:[],warnings:[]})
assert.equal(runSoundOutcome(run('review_withheld',20)),'withheld','withheld must take priority over shortfall')
assert.equal(runSoundOutcome(run('no_feasible_plan',20)),'withheld','no feasible plan must take priority over shortfall')
assert.equal(runSoundOutcome(run('unknown',0)),'error','unknown run status is not a successful result')
assert.equal(runSoundOutcome(run('completed',20)),'shortfall')
assert.equal(runSoundOutcome(run('completed',0)),'complete')

const scenario=(status,simulation_status,shortfall=0)=>({id:'scenario',name:'fixture',status,simulation_status,controls:{delay_days:0,yield_percent:100,demand_percent:100,labour_percent:100,cash_percent:100},result:{strategies:[{id:'balanced',name:'Balanced',metrics:{shortfall_kg:shortfall}}]}})
assert.equal(scenarioSoundOutcome(scenario('COMPLETED','NO_FEASIBLE_PLAN',20)),'withheld')
assert.equal(scenarioSoundOutcome(scenario('UNKNOWN','',0)),'error')
assert.equal(scenarioSoundOutcome(scenario('COMPLETED','',20)),'shortfall')
console.log(JSON.stringify({status:'PASS',checks:8}))
