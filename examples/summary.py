import garlic
import trio


async def main() -> None:
    BATCH_SIZE = 10

    # instantiate client object
    client = garlic.Client()

    for i in range(5):
        # request BATCH_SIZE entries (offset so we chunk)
        response = await client.get_summary(offset=BATCH_SIZE * i, limit=BATCH_SIZE)
        for relay in response.relays:
            # nickname is optionally present
            relay_nick = relay.nickname if relay.nickname else "Unnamed"
            # dump the fingerprint and nickname
            print(f"{relay.fingerprint} {relay_nick}")


if __name__ == "__main__":
    trio.run(main)
