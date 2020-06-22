import trio
import garlic


async def main() -> None:
    client = garlic.Client()
    response = await client.get_details(
        flag=garlic.Flag.EXIT,
        fields=(
            "fingerprint",
            "exit_policy",
            "exit_policy_summary",
            "exit_policy_v6_summary",
        ),
        limit=10,
    )
    print("Fingerprint\t\t\t\t\tExit Policy (IPv4)\tExit Policy (IPv6)")
    for relay in response.relays:
        ipv4_summary = (
            relay.exit_policy_summary if relay.exit_policy_summary else "Rejects All"
        )
        ipv6_summary = (
            relay.exit_policy_v6_summary
            if relay.exit_policy_v6_summary
            else "Rejects All"
        )
        print(f"{relay.fingerprint}\t{ipv4_summary}\t\t{ipv6_summary}")


if __name__ == "__main__":
    trio.run(main)
