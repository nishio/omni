// from https://github.com/blu3mo/Scrapbox-Duplicator
import { exportPages, assertString } from "./deps.ts";

const sid = Deno.env.get("SID");
const project_name = Deno.env.get("PROJECT_NAME");

assertString(sid);

console.log(`Exporting a json file from "/${project_name}"...`);
const result = await exportPages(project_name, {
  sid,
  metadata: false,
});
if (!result.ok) {
  const error = new Error();
  error.name = `${result.value.name} when exporting a json file`;
  error.message = result.value.message;
  throw error;
}

Deno.writeTextFile(
  `${project_name}.json`,
  JSON.stringify(result.value, null, 2)
);
console.log(`OK, wrote "${project_name}.json"`);
