const { execSync } = require('child_process');
const fs = require('fs');
const https = require('https');

const token = execSync('"C:\\Users\\vidaf\\.stitch-mcp\\google-cloud-sdk\\bin\\gcloud.cmd" auth print-access-token', { encoding: 'utf8' }).trim();
process.env.STITCH_ACCESS_TOKEN = token;
process.env.GOOGLE_CLOUD_PROJECT = 'gen-lang-client-0074559032';

const screenIds = [
  '4fc15be89c46495d8751dfee080b7719',
  '68d7397e5a1247b199f8264538c8ad06',
  '6d1bc36af60d4981a4c1da5158b541e1',
  '937872f418ac4ea69d75e2a621bb8b99',
  'e8f6bd3b3d7c4548bc82f5bd9f0e4e81',
  'f70b43d83d2a40698fd7444b08ffc28c'
];

async function downloadUrl(url, dest) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        return downloadUrl(res.headers.location, dest).then(resolve).catch(reject);
      }
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        fs.writeFileSync(dest, data, 'utf8');
        resolve(data);
      });
    }).on('error', reject);
  });
}

async function run() {
  const summary = [];
  for (let i = 0; i < screenIds.length; i++) {
    const sid = screenIds[i];
    const payload = JSON.stringify({
      projectId: '2221523846207666554',
      screenId: sid
    });

    try {
      fs.writeFileSync('payload.json', payload, 'utf8');
      const resRaw = execSync('npx --yes @_davideast/stitch-mcp tool get_screen -f payload.json', {
        env: process.env,
        encoding: 'utf8'
      });
      const data = JSON.parse(resRaw);
      summary.push({
        index: i + 1,
        id: sid,
        title: data.title,
        deviceType: data.deviceType,
        htmlUrl: data.htmlCode?.downloadUrl,
        screenshotUrl: data.screenshot?.downloadUrl
      });

      if (data.htmlCode?.downloadUrl) {
        await downloadUrl(data.htmlCode.downloadUrl, `stitch_screen_${i + 1}.html`);
      }
    } catch (e) {
      console.error(`Error screen ${sid}:`, e.message);
    }
  }

  fs.writeFileSync('stitch_summary.json', JSON.stringify(summary, null, 2), 'utf8');
  console.log('SUMMARY:', JSON.stringify(summary, null, 2));
}

run();
