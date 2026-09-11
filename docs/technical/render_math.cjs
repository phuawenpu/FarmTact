// Local MathJax-to-SVG build helper. Reads only the supplied JSON on stdin.
const fs = require('node:fs');
const path = require('node:path');
const moduleRoot = path.resolve(process.argv[2]);
const { mathjax } = require(path.join(moduleRoot, 'js/mathjax.js'));
const { TeX } = require(path.join(moduleRoot, 'js/input/tex.js'));
const { SVG } = require(path.join(moduleRoot, 'js/output/svg.js'));
const { liteAdaptor } = require(path.join(moduleRoot, 'js/adaptors/liteAdaptor.js'));
const { RegisterHTMLHandler } = require(path.join(moduleRoot, 'js/handlers/html.js'));
const { AllPackages } = require(path.join(moduleRoot, 'js/input/tex/AllPackages.js'));
const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const document = mathjax.document('', {
  InputJax: new TeX({ packages: AllPackages }),
  OutputJax: new SVG({ fontCache: 'none' }),
});
const equations = JSON.parse(fs.readFileSync(0, 'utf8'));
const output = equations.map(({tex, display}) => {
  const result = adaptor.outerHTML(document.convert(tex, {display}));
  if (result.includes('data-mjx-error')) throw new Error('Equation failed to render: ' + tex);
  return result;
});
process.stdout.write(JSON.stringify(output));
