// src/test.ts
import { SNCFScraper } from './scraper';

async function main() {
    console.log('🚀 Starting SNCF scraper test...');

    const scraper = new SNCFScraper();

    try {
        const results = await scraper.searchTrains({
            origin: "RESARAIL_STA_8772570",
            destination: "RESARAIL_STA_8768600",
            date: new Date('2025-01-06T05:00:00.000Z')
        });

        console.log('\n📊 Results:');
        console.table(results);

    } catch (error) {
        console.error('❌ Error:', error);
    }
}

// Exécuter le test
main().catch(console.error);