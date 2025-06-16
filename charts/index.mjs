// import { createChart, LineSeries } from "./node_modules/lightweight-charts/dist/lightweight-charts.standalone.production.mjs";
import { createChart, CandlestickSeries, LineSeries } from "./node_modules/lightweight-charts/dist/lightweight-charts.standalone.development.mjs";

const w = 0.9 * window.innerWidth;
const h = 0.9 * window.innerHeight;
const container = document.getElementById("tv-chart");
const chart = createChart(container, { width: w, height: h });

const candlestickSeries = chart.addSeries(CandlestickSeries, {
    upColor: "#26a69a", downColor: "#ef5350", borderVisible: false,
    wickUpColor: "#26a69a", wickDownColor: "#ef5350",
});

const candlePath = window.location.href + "/ohlc.json";
const candleResp = await fetch(candlePath);
const candleJSON = await candleResp.json();
candlestickSeries.setData(candleJSON);

const indsPath = window.location.href + "/inds.json";
const indsResp = await fetch(indsPath);
const indsJSON = await indsResp.json();

const colors = ["#2962FF", "#FFA500"];
let i = 0;
for (const key in indsJSON) {
    const lineSeries = chart.addSeries(LineSeries, { color: colors[i++] });
    lineSeries.setData(indsJSON[key]);
}
chart.timeScale().resetTimeScale();
