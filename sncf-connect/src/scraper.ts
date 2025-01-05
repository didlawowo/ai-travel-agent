import { chromium } from 'playwright';
import { format } from 'date-fns';
import { UserAgentRotator } from './userAgentRotator';
import type { SearchParams, TrainResult } from './types';

export class SNCFScraper {
    private userAgentRotator: UserAgentRotator;
    private readonly API_URL = 'https://www.sncf-connect.com/bff/api/v1/itineraries';

    constructor() {
        this.userAgentRotator = new UserAgentRotator();
    }

    async searchTrains(params: SearchParams): Promise<TrainResult[]> {
        const browser = await chromium.launch({
            headless: false
        });

        const context = await browser.newContext({
            userAgent: this.userAgentRotator.next(),
            viewport: { width: 1920, height: 1080 },
            extraHTTPHeaders: {
                'Accept': 'application/json',
                'Accept-Language': 'fr-FR,fr;q=0.9',
                'x-bff-key': 'ah1MPO-izehIHD-QZZ9y88n-kku876',
                'virtual-env-name': 'master',
                'x-api-env': 'production',
                'Origin': 'https://www.sncf-connect.com',
                'Referer': 'https://www.sncf-connect.com/',
                'x-client-channel': 'web',
                'x-client-app-id': 'front-web',
                'x-device-class': 'desktop',
                'x-market-locale': 'fr_FR'
            }
        });

        try {
            const page = await context.newPage();

            console.log('🌍 Accès à la page SNCF Connect...');
            await page.goto('https://www.sncf-connect.com/');
            await page.waitForLoadState('networkidle');
            console.log('✅ Page chargée');

            const payload = {
                schedule: {
                    outward: {
                        date: format(params.date, "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"),
                        arrivalAt: false
                    }
                },
                mainJourney: {
                    origin: {
                        id: params.origin,
                        codes: []
                    },
                    destination: {
                        id: params.destination,
                        codes: []
                    }
                },
                passengers: [{
                    typology: "ADULT",
                    withoutSeatAssignment: false
                }],
                forceDisplayResults: true,
                trainExpected: true,
                directJourney: false
            };

            console.log('📡 Envoi de la requête à l\'API...', {
                url: this.API_URL,
                payload: JSON.stringify(payload, null, 2)
            });

            const response = await page.request.post(this.API_URL, {
                data: payload,
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const responseData = await response.json();
            console.log('📥 Réponse reçue:', JSON.stringify(responseData, null, 2));

            const results = this.parseResults(responseData);
            console.log('🔍 Résultats parsés:', results);

            return results;

        } catch (error) {
            console.error('🚨 Error during scraping:', error);
            throw error;
        } finally {
            await browser.close();
        }
    }



    private parseResults(response: any): TrainResult[] {
        if (!response?.longDistance?.proposals?.proposals) {
            return [];
        }

        return response.longDistance.proposals.proposals.map((proposal: { id: any; departure: { timeLabel: any; originStationLabel: any; }; arrival: { timeLabel: any; destinationStationLabel: any; }; durationLabel: any; bestPriceLabel: any; transporterDescription: any; segments: string | any[]; }) => ({
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