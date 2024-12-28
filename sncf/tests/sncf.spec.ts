import { chromium } from 'playwright';
import { format } from 'date-fns';

interface SearchParams {
    origin: string;      // Station code (e.g., "RESARAIL_STA_8772570")
    destination: string; // Station code (e.g., "RESARAIL_STA_8768600")
    date: Date;         // Date de départ
}



// 🎭 user-agents.ts
export class UserAgentRotator {
    private userAgents: string[];
    private currentIndex: number;

    constructor() {
        // 📱 Liste de User-Agents réalistes et récents
        this.userAgents = [
            // 🖥️ Desktop - Chrome
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            // 🦊 Desktop - Firefox
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
            // 🧭 Desktop - Safari
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            // 📱 Mobile - iOS
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            // 🤖 Mobile - Android
            'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36',
        ];
        this.currentIndex = 0;
    }

    // 🔄 Obtient le prochain User-Agent de manière rotative
    public next(): string {
        const userAgent = this.userAgents[this.currentIndex];
        this.currentIndex = (this.currentIndex + 1) % this.userAgents.length;
        return userAgent;
    }

    // 🎲 Obtient un User-Agent aléatoire
    public random(): string {
        const randomIndex = Math.floor(Math.random() * this.userAgents.length);
        return this.userAgents[randomIndex];
    }
}



export class SNCFScraper {
    private userAgentRotator: UserAgentRotator;

    constructor() {
        this.userAgentRotator = new UserAgentRotator();
    }

    async searchTrains(params: SearchParams) {
        const browser = await chromium.launch();
        const context = await browser.newContext({
            userAgent: this.userAgentRotator.next(),
            viewport: {
                width: 1920,
                height: 1080
            }
        });

        try {
            const page = await context.newPage();

            // 📍 Ajout des headers spécifiques à SNCF Connect
            await page.setExtraHTTPHeaders({
                'x-bff-key': 'ah1MPO-izehIHD-QZZ9y88n-kku876',
                'virtual-env-name': 'master',
                'x-api-env': 'production',
                'Accept': 'application/json'
            });

            // 🔍 Le reste du code de recherche...
            const payload = {
                schedule: {
                    outward: {
                        date: format(params.date, "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"),
                        arrivalAt: false
                    }
                },
                mainJourney: {
                    origin: { id: params.origin },
                    destination: { id: params.destination }
                },
                passengers: [{
                    typology: "ADULT",
                    withoutSeatAssignment: false
                }],
                forceDisplayResults: true,
                trainExpected: true
            };

            // 📡 Appel API
            const response = await page.evaluate(
                async ({ url, data, headers }) => {
                    const res = await fetch(url, {
                        method: 'POST',
                        headers,
                        body: JSON.stringify(data)
                    });
                    return res.json();
                },
                {
                    url: 'https://www.sncf-connect.com/bff/api/v1/itineraries',
                    data: payload,
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );

            return this.parseResults(response);

        } catch (error) {
            console.error('🚨 Error during scraping:', error);
            throw error;
        } finally {
            await browser.close();
        }
    }

    private parseResults(response: any) {
        if (!response?.longDistance?.proposals?.proposals) {
            return [];
        }

        return response.longDistance.proposals.proposals.map(proposal => ({
            id: proposal.id,
            departure: {
                time: proposal.departure.timeLabel,
                station: proposal.departure.originStationLabel
            },
            arrival: {
                time: proposal.arrival.timeLabel,
                station: proposal.arrival.destinationStationLabel
            },
            duration: proposal.durationLabel,
            price: proposal.bestPriceLabel,
            type: proposal.transporterDescription,
            isDirectTrain: !proposal.segments?.length
        }));
    }
}

// 🎯 Exemple d'utilisation
async function main() {
    const scraper = new SNCFScraper();

    const results = await scraper.searchTrains({
        origin: "RESARAIL_STA_8772570",      // Mâcon Loché TGV
        destination: "RESARAIL_STA_8768600",  // Paris Gare de Lyon
        date: new Date('2025-01-06T05:00:00.000Z')
    });

    console.table(results);
}