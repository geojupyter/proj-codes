import projCodesJson from "./proj-codes.json" with { type: "json" };

export interface IProjInfo {
  auth_name: string;
  code: string;
  name: string;
  proj4string: string;
}

const projCodes: Record<string, IProjInfo> = projCodesJson;

export {projCodes};
export default projCodes;
