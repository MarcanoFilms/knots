#!/usr/bin/env python3
# Copyright (c) 2026 The Bitcoin Knots developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Rolling maturity coverage ends at the end coin height and starts at the enforce height."""
from test_framework.blocktools import add_witness_commitment, create_block, create_coinbase
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, assert_raises_rpc_error
from test_framework.wallet import MiniWallet

START = 200    # first covered coin height
ENFORCE = 320  # first height enforcing the rolling rule
DEPTH = 300
END = 203      # first non-covered coin height (zero-subsidy analog)


class RollingMaturityEndBoundTest(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 1
        self.setup_clean_chain = True
        self.extra_args = [[
            f"-testcoinbasematurityrolling={START}:{ENFORCE}:{DEPTH}:{END}",
            "-checkmempool=1",
        ]]

    def block(self, txs=None):
        node = self.nodes[0]
        height = node.getblockcount() + 1
        tip = node.getbestblockhash()
        block = create_block(int(tip, 16), create_coinbase(
            height, script_pubkey=self.mini.get_output_script()),
            node.getblockheader(tip)["time"] + 1,
            height=height, txlist=txs)
        add_witness_commitment(block)
        block.solve()
        return block

    def submit(self, block, expected=None):
        assert_equal(self.nodes[0].submitblock(block.serialize().hex()), expected)

    def spend(self, height):
        node = self.nodes[0]
        self.mini.rescan_utxos()
        txid = node.getblock(node.getblockhash(height))["tx"][0]
        return self.mini.create_self_transfer(utxo_to_spend=self.mini.get_utxo(txid=txid))

    def deployment(self):
        info = self.nodes[0].getdeploymentinfo()["deployments"]
        return info["rolling_coinbase_maturity"]

    def run_test(self):
        node = self.nodes[0]
        self.mini = MiniWallet(node)

        self.log.info("Deployment reports the last covered coin height")
        self.generate(self.mini, 310)
        dep = self.deployment()
        assert_equal(dep["type"], "flagday")
        assert_equal(dep["height"], ENFORCE)
        assert_equal(dep["coinbase_start_height"], START)
        assert_equal(dep["coinbase_end_height"], END - 1)
        assert_equal(dep["maturity"], DEPTH)
        assert_equal(dep["active"], False)

        self.log.info("Before enforcement a covered reward spends at 100, in mempool and in a block")
        pre = self.spend(START)  # depth 111: past 100, far short of DEPTH
        node.sendrawtransaction(pre["hex"])  # policy follows consensus: no early hold
        self.submit(self.block(txs=[pre["tx"]]))

        self.log.info("From enforcement covered rewards need the full depth")
        self.generate(self.mini, ENFORCE - node.getblockcount())
        assert node.getblockcount() >= ENFORCE
        assert_equal(self.deployment()["active"], True)
        covered = self.spend(START + 1)  # depth ~120 < DEPTH
        assert_raises_rpc_error(-26, "premature-spend-of-coinbase",
                                node.sendrawtransaction, covered["hex"])
        self.submit(self.block(txs=[covered["tx"]]), "bad-txns-premature-spend-of-coinbase")

        self.log.info("Rewards past the end coin height keep the historical 100")
        node.sendrawtransaction(self.spend(END)["hex"])
        self.generate(self.mini, 1)

        self.log.info("Rewards from before the start height are untouched too")
        node.sendrawtransaction(self.spend(START - 1)["hex"])
        self.generate(self.mini, 1)

        self.log.info("The rule survives a restart")
        self.restart_node(0, extra_args=self.extra_args[0])
        self.mini.rescan_utxos()
        assert_equal(self.deployment()["active"], True)
        assert_equal(self.deployment()["coinbase_end_height"], END - 1)
        still_covered = self.spend(START + 1)
        assert_raises_rpc_error(-26, "premature-spend-of-coinbase",
                                node.sendrawtransaction, still_covered["hex"])

        self.log.info("Exact depth boundary: DEPTH-1 fails, DEPTH succeeds")
        target = START + 1 + DEPTH  # first height whose block may spend coin START+1
        self.generate(self.mini, target - 2 - node.getblockcount())
        assert_equal(node.getblockcount(), target - 2)  # next block: depth DEPTH-1
        too_early = self.spend(START + 1)
        self.submit(self.block(txs=[too_early["tx"]]), "bad-txns-premature-spend-of-coinbase")
        self.generate(self.mini, 1)  # next block height == target: depth DEPTH
        at_depth = self.spend(START + 1)
        self.submit(self.block(txs=[at_depth["tx"]]))

        self.log.info("The last covered reward unlocks at its own full depth")
        assert_equal(node.getblockcount() + 1, END - 1 + DEPTH)
        node.sendrawtransaction(self.spend(END - 1)["hex"])
        self.generate(self.mini, 1)


if __name__ == '__main__':
    RollingMaturityEndBoundTest(__file__).main()
