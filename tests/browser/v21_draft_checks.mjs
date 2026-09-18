/** Fixture-only UI checks: invoke after the ordinary read-only UX checks while
 * FarmerWorkflow is mounted with calculated options. All writes are intercepted.
 * These assertions verify draft UI behavior, never backend mutation acceptance.
 * await runDraftChecks({ page, session, check });
 */
export async function runDraftChecks({ page, session, check }) {
  const fixture = { kind: 'intercepted-ui-only', writes: [], unexpectedWrites: [] };
  let proposalMode = 'failure', questionMode = 'failure';
  let snapshot = structuredClone(session);
  const fakeProposal = { id: 'fixture-draft-proposal', base_revision: snapshot.revision };
  const fakeConversation = { id: 'fixture-draft-conversation', messages: [], last_request_status: 'COMPLETED' };
  const respond = (route, status, body) => route.fulfill({status, contentType:'application/json', body:JSON.stringify(body)});
  const handler = async route => {
    const request = route.request(), path = new URL(request.url()).pathname, method = request.method();
    if (method === 'GET' && path.endsWith(`/planning-sessions/${session.id}`)) return respond(route,200,snapshot);
    if (method === 'GET' && path.endsWith(`/conversations/${fakeConversation.id}`)) return respond(route,200,fakeConversation);
    if (method === 'GET' || method === 'HEAD') return route.fallback();
    fixture.writes.push({method,path,intercepted:true});
    if (method === 'POST' && path.endsWith('/farm-workflow/proposals')) {
      if (proposalMode === 'failure') return respond(route,503,{detail:'Fixture proposal failure; no server write'});
      return respond(route,200,{...fakeProposal,base_revision:snapshot.revision});
    }
    if (method === 'POST' && path.endsWith(`/farm-workflow/proposals/${fakeProposal.id}/apply`)) return respond(route,200,fakeProposal);
    if (method === 'POST' && path.endsWith('/conversations')) {
      if (questionMode === 'failure') return respond(route,503,{detail:'Fixture specialist failure; no provider call'});
      return respond(route,200,{id:fakeConversation.id,status:'COMPLETED'});
    }
    if (method === 'POST' && path.endsWith(`/conversations/${fakeConversation.id}/messages`)) return respond(route,200,{id:'fixture-message-request',status:'COMPLETED'});
    fixture.unexpectedWrites.push({method,path});
    return respond(route,503,{detail:'Fixture guard blocked unexpected write'});
  };
  await page.route('**/api/**',handler);
  const dialog = () => page.getByRole('dialog',{name:'Challenge constraints and recalculate'});
  const openProposal = async () => {
    await page.getByRole('button',{name:'Apply & Recalculate',exact:true}).click();
    await dialog().waitFor();
  };
  const close = async () => { await page.keyboard.press('Escape'); await page.getByRole('dialog').waitFor({state:'hidden'}); };
  const select = async name => page.locator('.proposal-card').filter({hasText:name}).click();
  const fields = ['Expected demand','Seasonal yield','Harvest delay','Reserve a bed','Reservation starts','Reservation ends','Nursery sites','Labour hours/week','Cash capacity (SGD)','Add confirmed order (kg)','Add tentative order (kg)'];
  const values = async () => Object.fromEntries(await Promise.all(fields.map(async name => [name,await dialog().getByLabel(name,{exact:true}).inputValue()])));
  const mark = (name,pass,detail) => check(`fixture UI: ${name}`,pass,detail);
  try {
    const names = snapshot.result.strategies.map(item=>item.name);
    const [first,second] = names;
    if (!first || !second) throw Error('Draft fixture needs two calculated strategies');
    await select(first); await openProposal();
    await dialog().getByLabel('Expected demand',{exact:true}).fill('123');
    await dialog().getByLabel('Seasonal yield',{exact:true}).fill('81');
    await dialog().getByLabel('Harvest delay',{exact:true}).fill('4');
    await dialog().getByLabel('Reserve a bed',{exact:true}).selectOption(snapshot.farm.beds[0].id);
    const start = snapshot.farm.planning_date || snapshot.farm.cutoff.slice(0,10);
    await dialog().getByLabel('Reservation starts',{exact:true}).fill(start);
    const end = new Date(`${start}T00:00:00Z`);end.setUTCDate(end.getUTCDate()+5);
    await dialog().getByLabel('Reservation ends',{exact:true}).fill(end.toISOString().slice(0,10));
    for (const [name,value] of [['Nursery sites','213'],['Labour hours/week','34'],['Cash capacity (SGD)','987'],['Add confirmed order (kg)','12'],['Add tentative order (kg)','7']]) await dialog().getByLabel(name,{exact:true}).fill(value);
    const original=await values(); await close(); await openProposal();
    mark('all proposal edits survive Escape/reopen',JSON.stringify(await values())===JSON.stringify(original),original);
    await dialog().getByRole('button',{name:'Close Challenge constraints and recalculate'}).click(); await openProposal();
    mark('proposal edits survive close button/reopen',JSON.stringify(await values())===JSON.stringify(original));
    await close(); await select(second); await openProposal();
    mark('proposal draft does not cross strategy',await dialog().getByLabel('Expected demand',{exact:true}).inputValue()==='100');
    await close(); await select(first); await openProposal();
    mark('returning to original strategy restores its draft',JSON.stringify(await values())===JSON.stringify(original));
    await dialog().getByRole('button',{name:'Apply & Recalculate',exact:true}).click();
    await page.getByText('Fixture proposal failure; no server write',{exact:true}).waitFor();
    await close(); await openProposal();
    mark('failed explicit proposal submission retains all edits',JSON.stringify(await values())===JSON.stringify(original));
    proposalMode='success';
    const acceptedRead=page.waitForResponse(response=>response.request().method()==='GET' && new URL(response.url()).pathname.endsWith(`/planning-sessions/${session.id}`));
    await dialog().getByRole('button',{name:'Apply & Recalculate',exact:true}).click();
    await dialog().waitFor({state:'hidden'});
    // Wait for onDone's read before reopening; this fixture deliberately keeps revision unchanged.
    await (await acceptedRead).finished();
    await openProposal();
    mark('fixture accepted proposal clears same-context draft',await dialog().getByLabel('Expected demand',{exact:true}).inputValue()==='100' && await dialog().getByLabel('Add confirmed order (kg)',{exact:true}).inputValue()==='0');
    await dialog().getByLabel('Expected demand',{exact:true}).fill('132'); await close();
    await select(second); await openProposal();
    snapshot={...snapshot,revision:snapshot.revision+1};
    await dialog().getByRole('button',{name:'Apply & Recalculate',exact:true}).click(); await dialog().waitFor({state:'hidden'});
    await page.getByText(new RegExp(`Session revision ${snapshot.revision} · Council`)).waitFor();
    await select(first); await openProposal();
    mark('old unsent strategy draft does not cross revision',await dialog().getByLabel('Expected demand',{exact:true}).inputValue()==='100'); await close();

    const openSpecialist = async () => { await page.getByRole('button',{name:'Ask this specialist',exact:true}).first().click(); await page.getByRole('dialog',{name:'Ask a planning specialist'}).waitFor(); };
    const specialist = () => page.getByRole('dialog',{name:'Ask a planning specialist'});
    await openSpecialist();
    const advisors=await specialist().getByLabel('Specialist',{exact:true}).locator('option').evaluateAll(items=>items.map(item=>item.value));
    const advisorA=await specialist().getByLabel('Specialist',{exact:true}).inputValue();
    const advisorB=advisors.find(id=>id!==advisorA);
    if(!advisorB)throw Error('Draft fixture needs two advisers');
    await specialist().getByLabel('Question',{exact:true}).fill('Unsent fixture question for adviser A');
    await close(); await openSpecialist();
    mark('specialist question survives Escape/reopen',await specialist().getByLabel('Question',{exact:true}).inputValue()==='Unsent fixture question for adviser A');
    await specialist().getByLabel('Specialist',{exact:true}).selectOption(advisorB);
    mark('question does not leak to another adviser',await specialist().getByLabel('Question',{exact:true}).inputValue()!=='Unsent fixture question for adviser A');
    await specialist().getByLabel('Question',{exact:true}).fill('Unsent fixture question for adviser B');
    await specialist().getByLabel('Specialist',{exact:true}).selectOption(advisorA);
    mark('switching back restores adviser-specific question',await specialist().getByLabel('Question',{exact:true}).inputValue()==='Unsent fixture question for adviser A');
    await specialist().getByRole('button',{name:'Ask specialist',exact:true}).click();
    await page.getByText('Fixture specialist failure; no provider call',{exact:true}).waitFor();
    await close(); await openSpecialist();
    mark('failed explicit specialist submission retains question',await specialist().getByLabel('Question',{exact:true}).inputValue()==='Unsent fixture question for adviser A');
    questionMode='success';
    const acceptedQuestion=page.waitForResponse(response=>response.request().method()==='POST' && new URL(response.url()).pathname.endsWith(`/conversations/${fakeConversation.id}/messages`));
    await specialist().getByRole('button',{name:'Ask specialist',exact:true}).click();
    await (await acceptedQuestion).finished();
    await specialist().getByRole('button',{name:'Ask specialist',exact:true}).waitFor();
    await close(); await openSpecialist();
    mark('fixture accepted question clears reopened draft',await specialist().getByLabel('Question',{exact:true}).inputValue()==='');
    await specialist().getByLabel('Specialist',{exact:true}).selectOption(advisorB);
    mark('accepting one question preserves another adviser draft',await specialist().getByLabel('Question',{exact:true}).inputValue()==='Unsent fixture question for adviser B');
    await close();
    mark('fixture guard saw no unexpected writes',fixture.unexpectedWrites.length===0,fixture);
    return fixture;
  } finally { await page.unroute('**/api/**',handler); }
}
