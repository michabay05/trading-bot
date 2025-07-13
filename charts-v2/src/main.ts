import {
    createChart, ColorType, LineStyle, CrosshairMode, CandlestickSeries,
    HistogramSeries,
    type ChartOptions, type DeepPartial, type OhlcData, type HistogramData,
    type IChartApi, type UTCTimestamp, type ISeriesApi
} from "lightweight-charts";


interface _IOhlcvData {
    timestamp: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
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

async function fetchJSONData(symbol: string): Promise<[_IOhlcvData[], _IIndsRenderData[]]> {
    const symbolInfoPath: string = `${symbol}.json`
    const symbolInfoResp = await fetch(symbolInfoPath);
    const symbolInfoJSON = await symbolInfoResp.json();
    const candleData: _IOhlcvData[] = symbolInfoJSON["candles"];
    const indicatorData: _IIndsRenderData[] = symbolInfoJSON["indicators"];

    return [candleData, indicatorData];
}

function setupChart(container: HTMLDivElement): IChartApi {
    return createChart(container, {
        width: container.clientWidth,
        height: container.clientHeight,
        timeScale: {
            visible: true,
        },
        rightPriceScale: {
            visible: true,
        },
        ...COMMON_CHART_CONFIG
    });
}

function reformatOhlcvData(ohlcvData: _IOhlcvData[]): [OhlcData[], HistogramData[]] {
    let ohlcData: OhlcData[] = [];
    let volData: HistogramData[] = [];
    for (let i = 0; i < ohlcvData.length; i++) {
        let timeValue = Date.parse(ohlcvData[i]["timestamp"]) as UTCTimestamp;

        ohlcData.push({
            time: timeValue,
            open: ohlcvData[i]["open"],
            high: ohlcvData[i]["high"],
            low: ohlcvData[i]["low"],
            close: ohlcvData[i]["close"],
        });

        volData.push({
            time: timeValue,
            value: ohlcvData[i]["volume"],
            color: "#947DC9"
        })
    }

    return [ohlcData, volData];
}

async function renderData(
    symbol: string, candleSeries: ISeriesApi<"Candlestick">,
    volumeSeries: ISeriesApi<"Histogram">,
): Promise<void> {
    const [ohlcvData, indicatorData] = await fetchJSONData(symbol);
    const [ohlcData, volumeData] = reformatOhlcvData(ohlcvData);

    candleSeries.setData(ohlcData);
    volumeSeries.setData(volumeData);

    console.warn("Indicators are yet to be implemented.");
}


let MAIN_CHART: IChartApi;
let CHART_CONTAINER: HTMLDivElement;

window.addEventListener("load", () => {
    const containerID = "chart-container";
    const container = document.getElementById(containerID);
    if (!container) {
        console.error(`Could not find ${containerID}`);
        throw new Error();
    }

    const alternatorID = "alternator-btn";
    const alternatorBtn = document.getElementById(alternatorID);
    if (!alternatorBtn) {
        console.error(`Could not find ${containerID}`);
        throw new Error();
    }
    const alternator = alternatorBtn as HTMLButtonElement;

    CHART_CONTAINER = container as HTMLDivElement;
    MAIN_CHART = setupChart(CHART_CONTAINER);
    const candleSeries: ISeriesApi<"Candlestick"> = MAIN_CHART.addSeries(CandlestickSeries, {}, 0);
    const volSeries: ISeriesApi<"Histogram"> = MAIN_CHART.addSeries(HistogramSeries, {}, 1);

    let symbol = "AAPL";
    alternator.addEventListener("click", () => {
        if (symbol === "AAPL") {
            symbol = "SPY";
        } else {
            symbol = "AAPL";
        }
        console.log(`Symbol: ${symbol}`);
        renderData(symbol, candleSeries, volSeries);
    });

    renderData(symbol, candleSeries, volSeries);
});

window.addEventListener("resize", () => {
    MAIN_CHART.resize(CHART_CONTAINER.clientWidth, CHART_CONTAINER.clientHeight);
});

const COMMON_CHART_CONFIG: DeepPartial<ChartOptions> = {
    layout: {
        background: {
            type: ColorType.Solid,
            color: "#181818",
        },
        textColor: "#f0f0f0",
        // attributionLogo: false,
    },
    grid: {
        vertLines: {
            color: "#3e3e3e",
            style: LineStyle.Solid,
            visible: true,
        },
        horzLines: {
            color: "#3e3e3e",
            style: LineStyle.Solid,
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
        mode: CrosshairMode.Normal,
        // Vertical crosshair line (showing Date in Label)
        vertLine: {
            width: 1,
            color: "#C3BCDB44",
            style: LineStyle.LargeDashed,
            labelBackgroundColor: "#9B7DFF",
        },

        // Horizontal crosshair line (showing Price in Label)
        horzLine: {
            color: "#9B7DFF",
            labelBackgroundColor: "#9B7DFF",
        },
    },
};
