import {
    createChart, CandlestickSeries, LineSeries, HistogramSeries
}  from "./node_modules/lightweight-charts/dist/lightweight-charts.standalone.development.mjs";

interface _IOhlcvData {
    timestamp: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
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

interface _LWIndsData {
    // This is purely for debugging purposes.
    timeStr: string;
    time: number;
    value?: number;
}

interface _IIndsRenderData {
    name: string;
    overlay: boolean;
    color: string,
    data: _LWIndsData[];
}

async function fetchJSONData(): Promise<[string, _IOhlcvData[], _IIndsRenderData[]]> {
    const ohlcvPath: string = window.location.href + "/ohlcv.json";
    const ohlcvResp = await fetch(ohlcvPath);
    const ohlcvJSON = await ohlcvResp.json();
    const symbol: string = ohlcvJSON["symbol"];
    const ohlcvData: _IOhlcvData[] = ohlcvJSON["data"];

    const indsPath: string = window.location.href + "/inds.json";
    const indsResp = await fetch(indsPath);
    const indsJSON: _IIndsRenderData[] = await indsResp.json();

    return [symbol, ohlcvData, indsJSON];
}

function createSeriesFromString(chart: any, color: string): any {
    return chart.addSeries(LineSeries, { color: color });
}

function renderOhlcv(chart: any, ohlcvData: _IOhlcvData[]): void {
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

    datapointsCount = ohlcvData.length;
    for (let i = 0; i < ohlcvData.length; i++) {
        let timeValue = Date.parse(ohlcvData[i]["timestamp"]);

        candlestickData.push({
            time: timeValue,
            open: ohlcvData[i]["open"],
            high: ohlcvData[i]["high"],
            low: ohlcvData[i]["low"],
            close: ohlcvData[i]["close"],
        });

        volumeData.push({
            time: timeValue,
            value: ohlcvData[i]["volume"],
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

function renderIndicators(mainChart: any, secondaryChart: any, indsJSON: _IIndsRenderData[]): void {
    for (const ind of indsJSON) {
        console.log(ind.name);
        let series;
        if (ind.overlay) {
            series = createSeriesFromString(mainChart, ind.color);
        } else {
            series = createSeriesFromString(secondaryChart, ind.color);
            secondarySeries = series;
        }
        for (let j = 0; j < ind.data.length; j++) {
            if (typeof ind.data[j].time == "string") {
                ind.data[j].time = Date.parse(ind.data[j].timeStr);
            }
        }
        series.setData(ind.data);
    }
}


// Step 2: Sync crosshair position
function getCrosshairDataPoint(series: any, param: any) {
    if (!param.time) {
        return null;
    }
    const dataPoint = param.seriesData.get(series);
    return dataPoint || null;
}

function syncCrosshair(chart: any, series: any, dataPoint: any) {
    // Source: https://tradingview.github.io/lightweight-charts/tutorials/how_to/set-crosshair-position
    if (dataPoint) {
        chart.setCrosshairPosition(dataPoint.value, dataPoint.time, series);
        return;
    }
    chart.clearCrosshairPosition();
}

/* =================================================== */

let candlestickSeries: any, secondarySeries: any, datapointsCount: number;
let mainChart: any, secondaryChart: any;

window.onload = async () => {
    const w = 0.85 * window.innerWidth;
    const mainContainer = document.getElementById("main-chart");
    if (mainContainer === null) {
        console.error("Unable to find element with id 'main-chart'");
        throw Error();
    }
    const body: HTMLBodyElement = document.body as HTMLBodyElement;
    const backgroundColor: string = "#181818";
    body.style.backgroundColor = backgroundColor;
    const textColor: string = "#F0F0F0";
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
                style: 0, // LineStyle.Solid,
                visible: true,
            },
            horzLines: {
                color: gridLineColor,
                style: 0, // LineStyle.Solid,
                visible: true,
            },
        },
        localization: {
            timeFormatter: (unixTimestampMs: number) => {
                return new Date(unixTimestampMs).toLocaleString("en-US", {
                    hour12: false,
                });
            },
            // This dateFormat thing does not work
            dateFormat: "yyyy-MM-dd"
        },
        crosshair: {
            mode: 0, // CrosshairMode.Normal,
            // Vertical crosshair line (showing Date in Label)
            vertLine: {
                width: 8,
                color: "#C3BCDB44",
                style: 0, // LineStyle.Solid,
                labelBackgroundColor: "#9B7DFF",
            },

            // Horizontal crosshair line (showing Price in Label)
            horzLine: {
                color: "#9B7DFF",
                labelBackgroundColor: "#9B7DFF",
            },
        },
        priceScale: {
            visible: true,
            ticksVisible: true,
        }
    };

    mainChart = createChart(mainContainer, {
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
    if (secondaryContainer === null) {
        console.error("Unable to find element with id 'secondary-chart'");
        throw Error();
    }
    secondaryChart = createChart(secondaryContainer, {
        width: w, height: 0.15 * window.innerHeight,
        ...commonChartConfig
    });

    const [symbol, ohlcvData, indsJSON] = await fetchJSONData();
    console.log(symbol);

    renderOhlcv(mainChart, ohlcvData);
    renderIndicators(mainChart, secondaryChart, indsJSON);

    document.addEventListener("keypress", e => {
        if (e.key === "0") {
            mainChart.timeScale().scrollToRealTime();
        } else if (e.key >= "1" && e.key <= "9") {
            const pct = 1 - (Number.parseInt(e.key) / 10);
            mainChart.timeScale().scrollToPosition(-pct * datapointsCount, false);
        }
    });

    // =========================================
    mainChart.timeScale().subscribeVisibleLogicalRangeChange((timeRange: any) => {
        if (!timeRange) return;
        secondaryChart.timeScale().setVisibleLogicalRange(timeRange);
    });

    secondaryChart.timeScale().subscribeVisibleLogicalRangeChange((timeRange: any) => {
        if (!timeRange) return;
        mainChart.timeScale().setVisibleLogicalRange(timeRange);
    });
    // =========================================

    // =========================================
    // Add info for user
    const mainInfoDiv = document.getElementById("main-info");

    const symbolEl = document.createElement("h2");
    symbolEl.classList.add("main-symbol-info");
    symbolEl.innerText = symbol;
    mainInfoDiv?.appendChild(symbolEl);

    const lastOhlcv = ohlcvData[ohlcvData.length - 1];
    let ohlcvForInfo: _LWCandleData = {
        "time": Date.parse(lastOhlcv["timestamp"]),
        "open": lastOhlcv["open"],
        "high": lastOhlcv["high"],
        "low": lastOhlcv["low"],
        "close": lastOhlcv["close"],
    };
    const ohlcvEl = document.createElement("h4");
    ohlcvEl.classList.add("main-ohlcv-info-parts");
    ohlcvEl.innerText = `O ${ohlcvForInfo.open}, H ${ohlcvForInfo.high}, L ${ohlcvForInfo.low}, C ${ohlcvForInfo.close}`
    mainInfoDiv?.appendChild(ohlcvEl);

    mainChart.subscribeCrosshairMove((param: any) => {
        const dataPointonMain = getCrosshairDataPoint(candlestickSeries, param);
        ohlcvForInfo = dataPointonMain;
        syncCrosshair(secondaryChart, secondarySeries, dataPointonMain);
        ohlcvEl.innerText = `O ${ohlcvForInfo.open}, H ${ohlcvForInfo.high}, L ${ohlcvForInfo.low}, C ${ohlcvForInfo.close}`
    });
    secondaryChart.subscribeCrosshairMove((param: any) => {
        const dataPointonSecondary = getCrosshairDataPoint(secondarySeries, param);
        syncCrosshair(mainChart, candlestickSeries, dataPointonSecondary);
    });
};

window.onresize = () => {
    // mainChart.resize(window.innerWidth, window.innerHeight);
    // secondaryChart.resize(window.innerWidth, window.innerHeight);
};

