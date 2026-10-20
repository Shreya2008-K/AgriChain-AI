import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

export default buildModule("AgriChainRegistryModule", (m) => {
  const registry = m.contract("AgriChainRegistry");
  return { registry };
});