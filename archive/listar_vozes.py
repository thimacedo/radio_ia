import asyncio
import edge_tts

async def main():
    vm = await edge_tts.VoicesManager.create()
    voices = vm.find(Language="pt-BR")
    for v in voices:
        print(f"Name: {v['Name']}, Gender: {v['Gender']}")

if __name__ == "__main__":
    asyncio.run(main())
