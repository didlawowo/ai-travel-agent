// src/types.ts
export interface SearchParams {
    origin: string;
    destination: string;
    date: Date;
}

export interface TrainResult {
    id: string;
    departure: {
        time: string;
        station: string;
    };
    arrival: {
        time: string;
        station: string;
    };
    duration: string;
    price: string;
    type: string;
    isDirectTrain: boolean;
}