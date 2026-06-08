const { emit, getToolFilePath, isSensitivePath, readHookPayload } = require("./hookUtils.cjs");

async function main() {
  const payload = await readHookPayload();
  const targetFile = getToolFilePath(payload);
  if (targetFile && isSensitivePath(targetFile)) {
    emit({
      decision: "block",
      reason: `Refusing to write ${targetFile} — sensitive file. Confirm explicitly with the user before retrying.`,
    });
  }
}

main().catch((error) => {
  process.stderr.write(`[hook] pre-tool-use failed: ${error.message}\n`);
  process.exitCode = 0;
});
