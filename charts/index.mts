import {
    createChart, CandlestickSeries, LineSeries, BaselineSeries, HistogramSeries,
}  from "./node_modules/lightweight-charts/dist/lightweight-charts.standalone.development.mjs";


let candlestickSeries: any, secondarySeries: any, datapointsCount: number;
let lineSeriesArr: any[] = [];

async function fetchJSONData(): Promise<[any, any]> {
    const ohlcvPath: string = window.location.href + "/ohlcv.json";
    const ohlcvResp = await fetch(ohlcvPath);
    const ohlcvJSON = await ohlcvResp.json();

    const indsPath: string = window.location.href + "/inds.json";
    const indsResp = await fetch(indsPath);
    const indsJSON = await indsResp.json();

    return [ohlcvJSON, indsJSON];
}

function createSeriesFromString(chart: any, seriesType: string): any {
    switch (seriesType) {
        case "line":
            return chart.addSeries(LineSeries, { color: "#80deea" });
        case "baseline":
            return chart.addSeries(BaselineSeries, {
                baseValue: { type: "price", price: 50 },
                topLineColor: "rgba(38, 166, 154, 1)",
                topFillColor1: "rgba(38, 166, 154, 0.28)",
                topFillColor2: "rgba(38, 166, 154, 0.05)",
                bottomLineColor: "rgba(239, 83, 80, 1)",
                bottomFillColor1: "rgba(239, 83, 80, 0.05)",
                bottomFillColor2: "rgba(239, 83, 80, 0.28)"
            });
        default: {
            const msg = `Unknown series type: '${seriesType}'`;
            alert(msg);
            throw new Error(msg);
        }
    }
}

interface _IOhlcvData {
    timestamp: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    trade_count?: number;
    vwap?: number;
}

interface _LWCandleData {
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
}

interface _LWVolumeData {
    time: number;
    value: number;
    color: string;
}

function renderOhlcv(chart: any, cndJSON: _IOhlcvData[]): void {
    candlestickSeries = chart.addSeries(CandlestickSeries, {
        upColor: "#26a69a", downColor: "#ef5350", borderVisible: false,
        wickUpColor: "#26a69a", wickDownColor: "#ef5350",
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
        color: "#26a69a",
        priceFormat: {
            type: "volume",
        },
        priceScaleId: "left", // set as an overlay by setting a blank priceScaleId
    })

    const candlestickData: _LWCandleData[] = [];
    const volumeData: _LWVolumeData[] = [];

    datapointsCount = cndJSON.length;
    for (let i = 0; i < cndJSON.length; i++) {
        let timeValue = Date.parse(cndJSON[i]["timestamp"]);

        candlestickData.push({
            time: timeValue,
            open: cndJSON[i]["open"],
            high: cndJSON[i]["high"],
            low: cndJSON[i]["low"],
            close: cndJSON[i]["close"],
        });

        volumeData.push({
            time: timeValue,
            value: cndJSON[i]["volume"],
            color: "#947DC9"
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
}

interface _IIndsData {
    time: string;
    value: number
}

interface _LWIndsData {
    time: number;
    value?: number
}

interface _IIndsRenderData {
    name: string;
    seriesType: string;
    overlay: boolean;
    data: _IIndsData[];
}

function renderIndicators(mainChart: any, secondaryChart: any, indsJSON: _IIndsRenderData[]) {
    for (const ind of indsJSON) {
        console.log(ind.name);
        const output: _LWIndsData[] = [];
        // const colors: string[] = ["#2962FF", "#FFA500", "#b39ddb", "#fff59d", "#faa1a4", "#80deea"];
        let series;
        if (ind.overlay) {
            series = createSeriesFromString(mainChart, ind.seriesType);
        } else {
            series = createSeriesFromString(secondaryChart, ind.seriesType);
            secondarySeries = series;
        }
        for (let j = 0; j < ind.data.length; j++) {
            const tmp: _LWIndsData = { "time": Date.parse(ind.data[j]["time"]) };
            const value = ind.data[j]["value"];
            if (value != 0.0) {
                tmp["value"] = value;
            }
            output.push(tmp);
        }
        series.setData(output);
    }
}

const w = 0.85 * window.innerWidth;
const mainContainer = document.getElementById("main-chart");
const body: HTMLBodyElement = document.body as HTMLBodyElement;
const backgroundColor: string = "#181818";
body.style.backgroundColor = backgroundColor;
const textColor: string = "#F0F0F0";
// const gridLineColor: string = "#F0F0F044";
const gridLineColor: string = "#3e3e3e";

const commonChartConfig = {
    layout: {
        background: {
            type: "solid",
            color: backgroundColor,
        },
        textColor: textColor,
        attributionLogo: false,
    },
    grid: {
        vertLines: {
            color: gridLineColor,
            style: 0 /* LineStyle.Solid */,
            visible: true,
        },
        horzLines: {
            color: gridLineColor,
            style: 0 /* LineStyle.Solid */,
            visible: true,
        },
    },
    localization: {
        timeFormatter: (unixTimestampMs: number) => {
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
        mode: 0,
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

const secondaryContainer = document.getElementById("secondary-chart");
const secondaryChart = createChart(secondaryContainer, {
    width: w, height: 0.15 * window.innerHeight,
    ...commonChartConfig
});

/* ===================== Syncing both charts ===================== */
// Source: https://tradingview.github.io/lightweight-charts/tutorials/how_to/set-crosshair-position
// Step 1: Sync the currently visible window
mainChart.timeScale().subscribeVisibleLogicalRangeChange((timeRange: any) => {
    if (timeRange) {
        secondaryChart.timeScale().setVisibleLogicalRange(timeRange);
    }
});

secondaryChart.timeScale().subscribeVisibleLogicalRangeChange((timeRange: any) => {
    if (timeRange) {
        mainChart.timeScale().setVisibleLogicalRange(timeRange);
    }
});

// Step 2: Sync crosshair position
function getCrosshairDataPoint(series: any, param: any) {
    if (!param.time) {
        return null;
    }
    const dataPoint = param.seriesData.get(series);
    return dataPoint || null;
}

function syncCrosshair(chart: any, series: any, dataPoint: any) {
    if (dataPoint) {
        chart.setCrosshairPosition(dataPoint.value, dataPoint.time, series);
        return;
    }
    chart.clearCrosshairPosition();
}

mainChart.subscribeCrosshairMove((param: any) => {
    const dataPointonMain = getCrosshairDataPoint(candlestickSeries, param);
    syncCrosshair(secondaryChart, secondarySeries, dataPointonMain);
});
secondaryChart.subscribeCrosshairMove((param: any) => {
    const dataPointonSecondary = getCrosshairDataPoint(secondarySeries, param);
    syncCrosshair(mainChart, candlestickSeries, dataPointonSecondary);
});

const [cndJSON, indsJSON] = await fetchJSONData();

renderOhlcv(mainChart, cndJSON);
renderIndicators(mainChart, secondaryChart, indsJSON);

document.addEventListener("keypress", e => {
    if (e.key === "0") {
        mainChart.timeScale().scrollToRealTime();
    } else if (e.key >= '1' && e.key <= '9') {
        const pct = 1 - (Number.parseInt(e.key) / 10);
        mainChart.timeScale().scrollToPosition(-pct * datapointsCount, false);
    }
})
