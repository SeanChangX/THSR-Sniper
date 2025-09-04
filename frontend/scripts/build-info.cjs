#!/usr/bin/env node

// Build info script to display version information
const buildTime = new Date().toISOString();
const buildVersion = buildTime.replace(/[:.]/g, '-').slice(0, -5);

console.log('🚀 Building THSR Sniper Frontend');
console.log('📅 Build Time:', buildTime);
console.log('🏷️  Build Version:', buildVersion);
console.log('📦 Output Directory: dist/');
console.log('');

// Write build info to a file for reference
const fs = require('fs');
const path = require('path');

const buildInfo = {
  buildTime,
  buildVersion,
  timestamp: Date.now()
};

// Ensure dist directory exists
const distDir = path.join(__dirname, '../dist');
if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir, { recursive: true });
}

fs.writeFileSync(
  path.join(distDir, 'build-info.json'),
  JSON.stringify(buildInfo, null, 2)
);

// Replace build time in index.html after build
const indexPath = path.join(distDir, 'index.html');
if (fs.existsSync(indexPath)) {
  let indexContent = fs.readFileSync(indexPath, 'utf8');
  indexContent = indexContent.replace('__BUILD_TIME__', buildTime);
  fs.writeFileSync(indexPath, indexContent);
  console.log('✅ Build time injected into index.html');
}

console.log('✅ Build info written to dist/build-info.json');
