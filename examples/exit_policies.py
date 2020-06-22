import garlic
import trio


async def main() -> None:
    client = garlic.Client(enable_cache=False)
    response = await client.get_details(
        flag=garlic.Flag.EXIT,
        fields=("fingerprint", "exit_policy_summary", "exit_policy_v6_summary"),
        limit=10,
    )

    print("Fingerprint\t\t\t\t\tExit Policy (IPv4)\tExit Policy (IPv6)\tHTTP Exits")
    for relay in response.relays:
        v4_policy = "Allows Exits" if relay.exit_policy_summary else "Rejects All"
        v6_policy = "Allows Exits" if relay.exit_policy_v6_summary else "Rejects All"

        has_http = 80 in relay.exit_policy_summary.accept_policy
        if not has_http and relay.exit_policy_v6_summary:
            has_http = 80 in relay.exit_policy_v6_summary.accept_policy

        print(
            f"{relay.fingerprint}\t{v4_policy}\t\t{v6_policy}"
            f"\t\t{['No','Yes'][has_http]}"
        )


if __name__ == "__main__":
    trio.run(main)
