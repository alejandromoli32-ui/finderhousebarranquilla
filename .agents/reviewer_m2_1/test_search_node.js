const fs = require('fs');
const path = require('path');

const dataPath = path.resolve(__dirname, '../../data/inmuebles_barranquilla.json');
const properties = JSON.parse(fs.readFileSync(dataPath, 'utf8'));

function normalizeText(str) {
  if (!str) return '';
  return str.toString().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
}

properties.forEach(p => {
  const parts = [
    p.title || '', p.neighborhood || '', p.zone || '', p.property_type || '',
    p.address || '', p.contact?.agency || '', p.contact?.agent_name || '',
    p.contact?.phone || '', p.contact?.whatsapp || '', p.description || '', p.id || ''
  ];
  p._searchBlob = normalizeText(parts.join(' '));
});

console.log('Total properties indexed:', properties.length);

const queries = ['golf', 'riomar', 'alto prado', 'campina', 'campiña', 'parqueadero', 'piscina', 'casa', 'apartamento'];
queries.forEach(q => {
  const tokens = normalizeText(q).split(/\s+/).filter(Boolean);
  const matched = properties.filter(p => tokens.every(t => p._searchBlob.includes(t)));
  console.log("Query '" + q + "' matched: " + matched.length);
});

// Compare 'campina' and 'campiña'
const match1 = properties.filter(p => p._searchBlob.includes(normalizeText('campina'))).length;
const match2 = properties.filter(p => p._searchBlob.includes(normalizeText('campiña'))).length;
console.log('Diacritics equivalence test (campina vs campiña):', match1 === match2 ? 'PASS' : 'FAIL', `(${match1} vs ${match2})`);

// Performance benchmark: 10,000 queries
const start = performance.now();
const testIterations = 10000;
for (let i = 0; i < testIterations; i++) {
  const q = queries[i % queries.length];
  const tokens = normalizeText(q).split(/\s+/).filter(Boolean);
  properties.filter(p => tokens.every(t => p._searchBlob.includes(t)));
}
const elapsed = performance.now() - start;
const avgLatencyMs = elapsed / testIterations;
console.log('Benchmark 10,000 queries total time:', elapsed.toFixed(2), 'ms; avg latency:', avgLatencyMs.toFixed(4), 'ms');
