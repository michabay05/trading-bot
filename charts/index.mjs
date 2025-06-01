// import { createChart, LineSeries } from "./node_modules/lightweight-charts/dist/lightweight-charts.standalone.production.mjs";
import { createChart, CandlestickSeries } from "./node_modules/lightweight-charts/dist/lightweight-charts.standalone.development.mjs";

const w = 0.9 * window.innerWidth;
const h = 0.9 * window.innerHeight;
const container = document.getElementById("tv-chart");
const chart = createChart(container, { width: w, height: h });

const candlestickSeries = chart.addSeries(CandlestickSeries, {
    upColor: "#26a69a", downColor: "#ef5350", borderVisible: false,
    wickUpColor: "#26a69a", wickDownColor: "#ef5350",
});

const readFile = (file) => {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = evt => resolve(evt.target.result);
        reader.onerror = evt => reject(evt.target.error);
        reader.readAsText(file);
    });
}

const candleCSV = document.getElementById("csv-input").files[0];
try {
    const content = await readFile(candleCSV);

    // Parse csv here
    let candles = [];
    let lines = content.split('\n');
    for (let i = 1; i < lines.length; i++) {
        let line = lines[i].trim();
        if (line.length == 0) continue;
        let parts = line.split(',');
        // { time: "2018-12-22", open: 75.16, high: 82.84, low: 36.16, close: 45.72 },
        // Example: 2024-01-02 04:00:00,36.0400,36.1000,36.0400,36.1000,453.0000
        // const unixTime = new Date(parts[0]).getTime() / 1000;
        const unixTime = new Date(parts[0]).getTime();
        const candle = {
            time: unixTime, // 2024-01-02 04:00:00
            open: parseFloat(parts[1]), // 36.0400
            high: parseFloat(parts[2]), // 36.1000
            low: parseFloat(parts[3]), // 36.0400
            close: parseFloat(parts[4]), // 36.1000
        };
        candles.push(candle);
    }
    console.log(candles);

    candlestickSeries.setData(candles);
} catch (error) {
    console.error('Error reading file:', error);
}
