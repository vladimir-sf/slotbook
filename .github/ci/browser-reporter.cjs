// CI-only reporter: no names, attachments, streams, bodies or failure values are serialized.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
module.exports = class Reporter {
  onBegin(config, suite) {
    this.ids = suite.allTests().map(test => 'QA-' + crypto.createHash('sha256').update(test.id).digest('hex'));
    this.rows = [];
    this.errored = false;
    if (process.env.SLOTBOOK_CI_PHASE === 'collect') this.write('browser-inventory.json', this.ids);
  }
  onTestEnd(test, result) {
    this.rows.push({id: 'QA-' + crypto.createHash('sha256').update(test.id).digest('hex'), outcome: result.status});
  }
  onError() { this.errored = true; }
  onEnd(result) {
    if (process.env.SLOTBOOK_CI_PHASE !== 'collect') this.write('browser-results.json', {
      candidate: process.env.SLOTBOOK_CANDIDATE_SHA256, ids: this.ids,
      rows: this.rows, status: this.errored ? 'failed' : result.status,
    });
  }
  write(name, value) {
    const destination = path.join(process.env.SLOTBOOK_CI_PRIVATE, name);
    fs.writeFileSync(destination, JSON.stringify(value), {mode: 0o600, flag: 'wx'});
  }
};
