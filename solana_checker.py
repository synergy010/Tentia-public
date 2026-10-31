import os
import asyncio
import time
from solders.pubkey import Pubkey
from solders.signature import Signature
from solana.rpc.async_api import AsyncClient  

try:
    from config.settings import SOLANA_RPC_URL, PAYMENT_WALLET, EXPECTED_MINIMUM_SOL
    RPC_URL = SOLANA_RPC_URL
    DESTINATION_WALLET = PAYMENT_WALLET
except ImportError:
    RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    DESTINATION_WALLET = os.getenv("PAYMENT_WALLET", "")
    EXPECTED_MINIMUM_SOL = float(os.getenv("EXPECTED_MINIMUM_SOL", "0.19"))

client = AsyncClient(RPC_URL)  

async def verify_transaction(txn_signature: str, retries: int = 5, wait_seconds: int = 3) -> bool:
    if not DESTINATION_WALLET:
        return False

    txn_signature = txn_signature.strip()

    try:
        sig = Signature.from_string(txn_signature)
    except Exception:
        return False

    txn_data = None
    for attempt in range(retries):
        try:
            txn = await client.get_transaction(sig, encoding="jsonParsed")
            txn_data = txn.value
            if txn_data is not None:
                break
        except Exception:
            pass
        await asyncio.sleep(wait_seconds)

    if txn_data is None:
        return False

    meta = txn_data.transaction.meta
    if meta.err is not None:
        return False

    for inner in (meta.inner_instructions or []):
        for instruction in inner.instructions:
            try:
                if hasattr(instruction, 'parsed') and instruction.parsed:
                    parsed = instruction.parsed
                    if parsed.get('type') == 'transfer':
                        info = parsed.get('info', {})
                        destination = info.get('destination')
                        lamports = int(info.get('lamports', 0))
                        sol_amount = lamports / 1_000_000_000

                        if destination == DESTINATION_WALLET and sol_amount >= EXPECTED_MINIMUM_SOL:
                            return True
            except Exception:
                continue

    for instruction in txn_data.transaction.transaction.message.instructions:
        try:
            if hasattr(instruction, 'parsed') and instruction.parsed:
                parsed = instruction.parsed
                if parsed.get('type') == 'transfer':
                    info = parsed.get('info', {})
                    destination = info.get('destination')
                    lamports = int(info.get('lamports', 0))
                    sol_amount = lamports / 1_000_000_000

                    if destination == DESTINATION_WALLET and sol_amount >= EXPECTED_MINIMUM_SOL:
                        return True
        except Exception:
            continue

    return False
