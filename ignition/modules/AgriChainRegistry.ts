
import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

const AgriChainRegistryModule = buildModule(
  "AgriChainRegistryModule",
  (m) => {
    const registry = m.contract("AgriChainRegistry");
    return { registry };
  }
);

export default AgriChainRegistryModule;
