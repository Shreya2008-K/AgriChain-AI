import { expect } from "chai";
import { network } from "hardhat";

describe("AgriChainRegistry Smart Contract", function () {
  let ethers: any;
  let registry: any;
  let admin: any;
  let recorder: any;
  let verifier: any;
  let unauthorizedUser: any;

  let RECORDER_ROLE: string;
  let VERIFIER_ROLE: string;

  // Batch states:
  // 0: None, 1: Registered, 2: HarvestRecorded, 3: QualityPending,
  // 4: QualityVerified, 5: QualityRejected, 6: Listed, 7: OfferAccepted, 8: Sold, 9: Cancelled
  const State = {
    None: 0,
    Registered: 1,
    HarvestRecorded: 2,
    QualityPending: 3,
    QualityVerified: 4,
    QualityRejected: 5,
    Listed: 6,
    OfferAccepted: 7,
    Sold: 8,
    Cancelled: 9,
  };

  before(async function () {
    const conn = await network.connect();
    ethers = conn.ethers;
    RECORDER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("RECORDER_ROLE"));
    VERIFIER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("VERIFIER_ROLE"));
  });

  beforeEach(async function () {
    [admin, recorder, verifier, unauthorizedUser] = await ethers.getSigners();

    const AgriChainRegistry = await ethers.getContractFactory("AgriChainRegistry");
    registry = await AgriChainRegistry.deploy();
    await registry.waitForDeployment();

    // Grant roles
    await registry.connect(admin).grantRole(RECORDER_ROLE, recorder.address);
    await registry.connect(admin).grantRole(VERIFIER_ROLE, verifier.address);
  });

  it("1. should grant DEFAULT_ADMIN_ROLE to deployer", async function () {
    const DEFAULT_ADMIN_ROLE = ethers.ZeroHash;
    expect(await registry.hasRole(DEFAULT_ADMIN_ROLE, admin.address)).to.be.true;
    expect(await registry.hasRole(RECORDER_ROLE, recorder.address)).to.be.true;
    expect(await registry.hasRole(VERIFIER_ROLE, verifier.address)).to.be.true;
  });

  it("2. should allow recorder to register a new crop batch", async function () {
    const batchId = ethers.keccak256(ethers.toUtf8Bytes("BATCH-2026-TOM-001"));
    const metaHash = ethers.keccak256(ethers.toUtf8Bytes("metadata-v1-facts"));

    const tx = await registry.connect(recorder).record(batchId, State.Registered, metaHash);
    await expect(tx)
      .to.emit(registry, "BatchEvent")
      .withArgs(batchId, State.Registered, metaHash, recorder.address);

    const b = await registry.batches(batchId);
    expect(b.state).to.equal(State.Registered);
    expect(b.metadataHash).to.equal(metaHash);
    expect(b.recorder).to.equal(recorder.address);
  });

  it("3. should execute full valid lifecycle to Sold", async function () {
    const batchId = ethers.keccak256(ethers.toUtf8Bytes("BATCH-2026-RICE-002"));
    const h1 = ethers.keccak256(ethers.toUtf8Bytes("reg"));
    const h2 = ethers.keccak256(ethers.toUtf8Bytes("harvest"));
    const h3 = ethers.keccak256(ethers.toUtf8Bytes("pending"));
    const h4 = ethers.keccak256(ethers.toUtf8Bytes("verified"));
    const h5 = ethers.keccak256(ethers.toUtf8Bytes("listed"));
    const h6 = ethers.keccak256(ethers.toUtf8Bytes("accepted"));
    const h7 = ethers.keccak256(ethers.toUtf8Bytes("sold"));

    // Registered
    await registry.connect(recorder).record(batchId, State.Registered, h1);
    // HarvestRecorded
    await registry.connect(recorder).record(batchId, State.HarvestRecorded, h2);
    // QualityPending
    await registry.connect(recorder).record(batchId, State.QualityPending, h3);
    // QualityVerified (by verifier)
    await registry.connect(verifier).record(batchId, State.QualityVerified, h4);
    // Listed
    await registry.connect(recorder).record(batchId, State.Listed, h5);
    // OfferAccepted
    await registry.connect(recorder).record(batchId, State.OfferAccepted, h6);
    // Sold
    await registry.connect(recorder).record(batchId, State.Sold, h7);

    const b = await registry.batches(batchId);
    expect(b.state).to.equal(State.Sold);
    expect(b.metadataHash).to.equal(h7);
  });

  it("4. should reject unauthorized non-verifier when verifying quality", async function () {
    const batchId = ethers.keccak256(ethers.toUtf8Bytes("BATCH-2026-WHEAT-003"));
    const h = ethers.keccak256(ethers.toUtf8Bytes("test"));

    await registry.connect(recorder).record(batchId, State.Registered, h);
    await registry.connect(recorder).record(batchId, State.HarvestRecorded, h);
    await registry.connect(recorder).record(batchId, State.QualityPending, h);

    // Recorder attempts to verify (has RECORDER_ROLE, but not VERIFIER_ROLE)
    let reverted = false;
    try {
      await registry.connect(recorder).record(batchId, State.QualityVerified, h);
    } catch (e: any) {
      reverted = true;
    }
    expect(reverted, "Recorder should not be able to verify quality").to.be.true;

    // Unauthorized user attempts to verify
    reverted = false;
    try {
      await registry.connect(unauthorizedUser).record(batchId, State.QualityVerified, h);
    } catch (e: any) {
      reverted = true;
    }
    expect(reverted, "Unauthorized user should not be able to verify quality").to.be.true;
  });

  it("5. should reject unauthorized non-recorder when registering batch", async function () {
    const batchId = ethers.keccak256(ethers.toUtf8Bytes("BATCH-UNAUTH-004"));
    const h = ethers.keccak256(ethers.toUtf8Bytes("test"));

    let reverted = false;
    try {
      await registry.connect(unauthorizedUser).record(batchId, State.Registered, h);
    } catch (e: any) {
      reverted = true;
    }
    expect(reverted, "Unauthorized user should not be able to register batch").to.be.true;
  });

  it("6. should revert on invalid state transition (skip stages)", async function () {
    const batchId = ethers.keccak256(ethers.toUtf8Bytes("BATCH-SKIP-005"));
    const h = ethers.keccak256(ethers.toUtf8Bytes("test"));

    // Attempting to jump directly from None to Sold
    await expect(
      registry.connect(recorder).record(batchId, State.Sold, h)
    ).to.be.revertedWith("Invalid transition");

    // Register
    await registry.connect(recorder).record(batchId, State.Registered, h);

    // Attempting to jump from Registered to Listed directly
    await expect(
      registry.connect(recorder).record(batchId, State.Listed, h)
    ).to.be.revertedWith("Invalid transition");
  });

  it("7. should support quality rejection path", async function () {
    const batchId = ethers.keccak256(ethers.toUtf8Bytes("BATCH-REJECT-006"));
    const h = ethers.keccak256(ethers.toUtf8Bytes("test"));

    await registry.connect(recorder).record(batchId, State.Registered, h);
    await registry.connect(recorder).record(batchId, State.HarvestRecorded, h);
    await registry.connect(recorder).record(batchId, State.QualityPending, h);
    await registry.connect(verifier).record(batchId, State.QualityRejected, h);

    const b = await registry.batches(batchId);
    expect(b.state).to.equal(State.QualityRejected);

    // Cannot list rejected batch
    await expect(
      registry.connect(recorder).record(batchId, State.Listed, h)
    ).to.be.revertedWith("Invalid transition");
  });

  it("8. should support cancellation path from Listed", async function () {
    const batchId = ethers.keccak256(ethers.toUtf8Bytes("BATCH-CANCEL-007"));
    const h = ethers.keccak256(ethers.toUtf8Bytes("test"));

    await registry.connect(recorder).record(batchId, State.Registered, h);
    await registry.connect(recorder).record(batchId, State.HarvestRecorded, h);
    await registry.connect(recorder).record(batchId, State.QualityPending, h);
    await registry.connect(verifier).record(batchId, State.QualityVerified, h);
    await registry.connect(recorder).record(batchId, State.Listed, h);

    // Cancel listing
    await registry.connect(recorder).record(batchId, State.Cancelled, h);
    const b = await registry.batches(batchId);
    expect(b.state).to.equal(State.Cancelled);
  });
});
