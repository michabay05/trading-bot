// import { createChart, LineSeries } from "./node_modules/lightweight-charts/dist/lightweight-charts.standalone.production.mjs";
import {
    createChart, CandlestickSeries, LineSeries, BaselineSeries, CrosshairMode, LastPriceAnimationMode,
    HistogramSeries
}  from "./node_modules/lightweight-charts/dist/lightweight-charts.standalone.development.mjs";

let candlestickSeries, volumeSeries, baselineSeries;
let lineSeriesArr = []

async function renderMainChart(chart) {
    candlestickSeries = chart.addSeries(CandlestickSeries, {
        upColor: "#26a69a", downColor: "#ef5350", borderVisible: false,
        wickUpColor: "#26a69a", wickDownColor: "#ef5350",
    });

    volumeSeries = chart.addSeries(HistogramSeries, {
        color: "#26a69a",
        priceFormat: {
            type: "volume",
        },
        priceScaleId: "left", // set as an overlay by setting a blank priceScaleId
    })

    // Candlestick data format: {time, open, high, low, close}
    const candlestickData = [];
    // Volume data format: {time, value, color}
    const volumeData = [];

    const ohlcvPath = window.location.href + "/ohlcv.json";
    const ohlcvResp = await fetch(ohlcvPath);
    const ohlcvJSON = await ohlcvResp.json();
    for (let i = 0; i < ohlcvJSON.length; i++) {
        let timeValue = Date.parse(ohlcvJSON[i]["Date"]);

        candlestickData.push({
            time: timeValue,
            open: ohlcvJSON[i]["Open"],
            high: ohlcvJSON[i]["High"],
            low: ohlcvJSON[i]["Low"],
            close: ohlcvJSON[i]["Close"],
        });

        volumeData.push({
            time: timeValue,
            value: ohlcvJSON[i]["Volume"],
            // color: ,
        })
    }

    candlestickSeries.priceScale().applyOptions({
        scaleMargins: {
            top: 0, // highest point of the series will be 70% away from the top
            bottom: 0.15,
        },
    })

    volumeSeries.priceScale().applyOptions({
        scaleMargins: {
            top: 0.85, // highest point of the series will be 70% away from the top
            bottom: 0,
        },
    })

    candlestickSeries.setData(candlestickData);
    volumeSeries.setData(volumeData);

    const indsPath = window.location.href + "/inds.json";
    const indsResp = await fetch(indsPath);
    const indsJSON = await indsResp.json();

    const colors = ["#2962FF", "#FFA500"];
    let i = 0;
    for (const key in indsJSON) {
        const lineSeries = chart.addSeries(LineSeries, { color: colors[i++] });
        for (let j = 0; j < indsJSON[key].length; j++) {
            let dateStr = indsJSON[key][j]["time"];
            indsJSON[key][j]["time"] = Date.parse(dateStr);
        }
        lineSeries.setData(indsJSON[key]);
        lineSeriesArr.push(lineSeries);
    }
    chart.timeScale().resetTimeScale();
}

async function renderSecondaryChart(chart) {
    baselineSeries = chart.addSeries(BaselineSeries, {
        baseValue: { type: "price", price: 47.25 },
        topLineColor: "rgba(38, 166, 154, 1)",
        topFillColor1: "rgba(38, 166, 154, 0.28)",
        topFillColor2: "rgba(38, 166, 154, 0.05)",
        bottomLineColor: "rgba(239, 83, 80, 1)",
        bottomFillColor1: "rgba(239, 83, 80, 0.05)",
        bottomFillColor2: "rgba(239, 83, 80, 0.28)"
    });

    const indsPath = window.location.href + "/inds.json";
    const indsResp = await fetch(indsPath);
    const indsJSON = await indsResp.json();

    const key = "EMA_2";
    const warmup = indsJSON[key]["warmup"]
    for (let j = 0; j < indsJSON[key].length; j++) {
        let dateStr = indsJSON[key][j]["time"];
        indsJSON[key][j]["time"] = Date.parse(dateStr);
    }
    baselineSeries.setData(indsJSON[key]);
    // for (const key in indsJSON) {
    //     for (let j = 0; j < indsJSON[key].length; j++) {
    //         let dateStr = indsJSON[key][j]["time"];
    //         indsJSON[key][j]["time"] = Date.parse(dateStr);
    //     }
    //     baselineSeries.setData(indsJSON[key]);
    // }
    chart.timeScale().resetTimeScale();
}

const w = 0.85 * window.innerWidth;
const mainContainer = document.getElementById("main-chart");
const commonChartConfig = {
    localization: {
        timeFormatter: unixTimestampMs => {
            return new Date(unixTimestampMs).toLocaleString("en-US", {
                dateStyle: "medium",
                timeStyle: "medium",
                hour12: false,
            });
        },
        // This dateFormat thing does not work
        dateFormat: "yyyy-MM-dd"
    },
    crosshair: {
        mode: CrosshairMode.Normal,
    },
    layout: {
        attributionLogo: false,
    },
    priceScale: {
        visible: true,
        ticksVisible: true,
    }
}
const mainChart = createChart(mainContainer, {
    width: w, height: 0.75 * window.innerHeight,
    timeScale: {
        visible: true,
    },
    // leftPriceScale: {
    //     visible: true,
    // },
    rightPriceScale: {
        visible: true,
    },
    ...commonChartConfig
});

const secondaryContainer = document.getElementById("secondary-chart")
const secondaryChart = createChart(secondaryContainer, {
    width: w, height: 0.15 * window.innerHeight,
    ...commonChartConfig
});

/* ===================== Syncing both charts ===================== */
// Source: https://tradingview.github.io/lightweight-charts/tutorials/how_to/set-crosshair-position
// Step 1: Sync the currently visible window
mainChart.timeScale().subscribeVisibleLogicalRangeChange(timeRange => {
    secondaryChart.timeScale().setVisibleLogicalRange(timeRange);
});

secondaryChart.timeScale().subscribeVisibleLogicalRangeChange(timeRange => {
    mainChart.timeScale().setVisibleLogicalRange(timeRange);
});

// Step 2: Sync crosshair position
function getCrosshairDataPoint(series, param) {
    if (!param.time) {
        return null;
    }
    const dataPoint = param.seriesData.get(series);
    return dataPoint || null;
}

function syncCrosshair(chart, series, dataPoint) {
    if (dataPoint) {
        chart.setCrosshairPosition(dataPoint.value, dataPoint.time, series);
        return;
    }
    chart.clearCrosshairPosition();
}

mainChart.subscribeCrosshairMove(param => {
    const dataPointCS = getCrosshairDataPoint(lineSeriesArr[0], param);
    syncCrosshair(secondaryChart, baselineSeries, dataPointCS);
});
secondaryChart.subscribeCrosshairMove(param => {
    const dataPointBS = getCrosshairDataPoint(baselineSeries, param);
    syncCrosshair(mainChart, lineSeriesArr[0], dataPointBS);
    // const dataPointVS = getCrosshairDataPoint(volumeSeries, param);
    // syncCrosshair(mainChart, volumeSeries, dataPointVS);
});

renderMainChart(mainChart);
renderSecondaryChart(secondaryChart);
