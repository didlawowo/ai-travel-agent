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