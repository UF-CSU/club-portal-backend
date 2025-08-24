import { render } from "@react-email/render";
import * as React from "react";
import * as fs from "fs";
import * as path from "path";
import InviteEmail from "../src/invite";

async function main() {
  const html = await render(
    React.createElement(InviteEmail, { club_name: "{{ club_name }}" }),
    { pretty: true }
  );

  const outputPath = path.resolve(
    __dirname,
    "../../email_invite_template.html"
  );

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, html); 
  console.log("Wrote:", outputPath);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
