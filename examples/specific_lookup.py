import garlic
import trio


async def main() -> None:
    # instantiate client object
    client = garlic.Client()
    fingerprint = "730E0D04D90CC0B15F320F6DFD5DD23752AD52E9"
    # lookup specific relay using its fingerprint
    response = await client.get_details(lookup=fingerprint)
    # output the contents of our matching relay
    print(response.relays[0])


if __name__ == "__main__":
    trio.run(main)
