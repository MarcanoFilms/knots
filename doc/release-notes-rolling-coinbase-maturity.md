Consensus
---------

- Rolling coinbase maturity (1 year). On mainnet, from block 979920, every
  generated coin mined at height 973440 or later must be buried 52560 blocks
  (365 days of 144 blocks) before it can be spent. Each reward counts from its
  own block, so exactly one reward unlocks per block, the first at 1026000.

  This replaces the shared release of the existing long coinbase maturity
  window: the rewards it holds (973440 to 979919) are no longer all released
  together at block 979920. Through block 979919 the rules are unchanged.
  Rewards mined before 973440 keep ordinary 100-block maturity.

  This rule is separate from RDTS. It is decided by block heights alone and
  does not depend on `RdtsExpiryTime` or the BLAKE2b fork, so it stays in force
  whether RDTS is extended or lapses.

  Coverage ends with issuance: rewards mined at height 6930000 (the first
  zero-subsidy height, 33 halvings) or later keep the maturity the other rules
  require. The end is set by the height a reward was mined at, not the height
  it is spent at, so every covered reward still waits its full 52560 blocks and
  nothing is released early. The last covered reward, mined at 6929999,
  unlocks at 6982559.

  Upgrading nodes check every block from 979920 again using the existing
  chainstate revalidation, under the marker `rolling_coinbase_maturity_1y`.
  A node that upgrades before block 979920 rewinds nothing. A pruned node that
  upgrades later and no longer has those blocks must reindex.

  `getdeploymentinfo` reports the rule as `rolling_coinbase_maturity`, and
  `getblocktemplate` lists `rolling_coinbase_maturity` in `rules` once it is
  active. Wallets and the GUI show the maturity that applies to each reward.
  Testnet4, signet and regtest are unchanged; regtest can opt in with
  `-testcoinbasematurityrolling=<start_height>:<enforce_height>:<maturity>[:<end_coin_height>]`.
