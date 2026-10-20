import { network } from "hardhat";

const CONTRACT_ADDRESS =
  "0x5FbDB2315678afecb367f032d93F642f64180aa3";

async function main() {
  const { ethers } = await network.connect();
  const [admin] = await ethers.getSigners();

  const registry = await ethers.getContractAt(
    "AgriChainRegistry",
    CONTRACT_ADDRESS,
    admin
  );

  const recorderRole = await registry.RECORDER_ROLE();
  const verifierRole = await registry.VERIFIER_ROLE();
  const account = await admin.getAddress();

  await (await registry.grantRole(recorderRole, account)).wait();
  await (await registry.grantRole(verifierRole, account)).wait();

  console.log("Permissions granted to:", account);
  console.log("Recorder:", await registry.hasRole(recorderRole, account));
  console.log("Verifier:", await registry.hasRole(verifierRole, account));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
