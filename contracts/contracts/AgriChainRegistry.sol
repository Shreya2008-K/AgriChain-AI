// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "@openzeppelin/contracts/access/AccessControl.sol";

/// @notice Stores only hashes/references. Does not prove physical accuracy of crop claims. NOT compiled or tested.
contract AgriChainRegistry is AccessControl {
    bytes32 public constant RECORDER_ROLE = keccak256("RECORDER_ROLE");
    bytes32 public constant VERIFIER_ROLE = keccak256("VERIFIER_ROLE");
    enum State { None, Registered, HarvestRecorded, QualityPending, QualityVerified, QualityRejected, Listed, OfferAccepted, Sold, Cancelled }
    struct Batch { State state; bytes32 metadataHash; address recorder; uint64 updatedAt; }
    mapping(bytes32 => Batch) public batches;
    event BatchEvent(bytes32 indexed batchId, State state, bytes32 metadataHash, address indexed actor);

    constructor() { _grantRole(DEFAULT_ADMIN_ROLE, msg.sender); }

    function _allowed(State a, State b) internal pure returns (bool) {
        return (a == State.None && b == State.Registered) || (a == State.Registered && b == State.HarvestRecorded)
            || (a == State.HarvestRecorded && b == State.QualityPending)
            || (a == State.QualityPending && (b == State.QualityVerified || b == State.QualityRejected))
            || (a == State.QualityVerified && b == State.Listed)
            || (a == State.Listed && (b == State.OfferAccepted || b == State.Cancelled))
            || (a == State.OfferAccepted && b == State.Sold);
    }
    function record(bytes32 id, State next, bytes32 metadataHash) external {
        if (next == State.QualityVerified || next == State.QualityRejected) _checkRole(VERIFIER_ROLE);
        else _checkRole(RECORDER_ROLE);
        Batch storage b = batches[id];
        require(_allowed(b.state, next), "Invalid transition");
        b.state = next; b.metadataHash = metadataHash; b.recorder = msg.sender; b.updatedAt = uint64(block.timestamp);
        emit BatchEvent(id, next, metadataHash, msg.sender);
    }
}
