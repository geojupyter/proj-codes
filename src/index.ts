import projCodesJson from "./_generated/proj-codes.json" with { type: "json" };

export interface IProjInfo {
  auth_name: string;
  code: string;
  name: string;
  proj4string: string;
  area_of_use: number[];
}

const projCodes: Record<string, IProjInfo> = projCodesJson;

export {projCodes};
export default projCodes;
