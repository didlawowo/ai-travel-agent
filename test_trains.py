from agents.tools.trains_finder import TrainsInput, trains_finder
from loguru import logger


def test_train_search():
    """Test de la recherche de trains"""

    # Configuration du test
    params = TrainsInput(
        origin_city="75056",  # Paris
        destination_city="69123",  # Lyon
        departure_date="2024-12-28",
        departure_time="12:17",
    )

    try:
        logger.info("🧪 Starting test query")
        logger.info(f"Parameters: {params}")

        # Utilisation de invoke au lieu de l'appel direct
        result = trains_finder.invoke({"params": params})

        # Affichage des résultats
        if result.get("status") == "success":
            logger.info(f"✅ Found {result['count']} trains")
            for idx, train in enumerate(result["trains"], 1):
                logger.info(f"\n🚂 Train {idx}:")
                logger.info(
                    f"🚉 Départ: {train['departure']['station']} à {train['departure']['time']}"
                )
                logger.info(
                    f"🏁 Arrivée: {train['arrival']['station']} à {train['arrival']['time']}"
                )
                logger.info(f"⏱️ Durée: {train['duration_minutes']} minutes")
                logger.info(f"🎫 Type: {train['train_type']} - {train['train_number']}")
                logger.info(f"🌍 CO2: {train['co2_emission']:.2f} gEC")

                # Affichage détaillé des tarifs
                fare_info = train["price"]
                if fare_info["found"]:
                    logger.info(
                        f"💰 Prix total: {fare_info['total']} {fare_info['currency']}"
                    )
                    if fare_info["tickets"]:
                        logger.info("📋 Détail des billets:")
                        for ticket in fare_info["tickets"]:
                            logger.info(
                                f"  - {ticket['name']}: {ticket['cost']} {ticket['currency']}"
                            )
                else:
                    logger.info("💰 Prix: Non disponible")

                if train["transfers"] == 0:
                    logger.info("✅ Train direct")
                else:
                    logger.info(f"🔄 Correspondances: {train['transfers']}")

                logger.info("──────────────────────")
        else:
            logger.error(f"❌ Search failed: {result.get('message', 'Unknown error')}")

    except Exception as e:
        logger.error(f"❌ Test error: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")

        # Debug info
        if "result" in locals():
            logger.debug(f"Last result structure: {result}")


if __name__ == "__main__":
    test_train_search()
