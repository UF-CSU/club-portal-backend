import { render } from "@react-email/render";
import * as React from "react";
import * as fs from "fs";
import * as path from "path";
import AccountSetupLink from "../src/account-setup-link";

async function main() {
  const html = await render(
    React.createElement(AccountSetupLink, { setup_url: "{{ setup_url }}" }),
    { pretty: true }
  );

  const outputPath = path.resolve(
    __dirname,
    "../../account-setup-link.html"
  );

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, html);
  console.log("Wrote:", outputPath);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
