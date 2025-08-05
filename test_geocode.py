import asyncio
from utils.geocoding import geocode_address, autocomplete_address
from bot.utils.escape import safe_html


async def main():
    address = safe_html("<b>Сочи Аишхо, 5</b>")
    print(address)
    print("🔍 Тест: geocode_address")
    coords = await geocode_address(address)
    if coords:
        print(f"Координаты: lat={coords[0]}, lon={coords[1]}")
    else:
        print("Не удалось получить координаты.")

    print("\n🔍 Тест: autocomplete_address")
    suggestions = await autocomplete_address("сочи Аишхо, 5")
    if suggestions:
        for i, s in enumerate(suggestions, 1):
            print(f"{i}. {s['label']} (lat={s['lat']}, lon={s['lon']})")
    else:
        print("Нет предложений.")

if __name__ == "__main__":
    asyncio.run(main())
