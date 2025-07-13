import {
    createChart, ColorType, LineStyle, CrosshairMode, CandlestickSeries,
    HistogramSeries,
    type ChartOptions, type DeepPartial, type OhlcData, type HistogramData,
    type IChartApi, type UTCTimestamp
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

async function fetchJSONData(): Promise<[string, _IOhlcvData[], _IIndsRenderData[]]> {
    const ohlcvPath: string = "ohlcv.json";
    const ohlcvResp = await fetch(ohlcvPath);
    const ohlcvJSON = await ohlcvResp.json();
    const symbol: string = ohlcvJSON["symbol"];
    const ohlcvData: _IOhlcvData[] = ohlcvJSON["data"];

    const indsPath: string = "inds.json";
    const indsResp = await fetch(indsPath);
    const indsJSON: _IIndsRenderData[] = await indsResp.json();

    return [symbol, ohlcvData, indsJSON];
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

async function render(chart: IChartApi): Promise<void> {
    const [symbol, ohlcvData, indsJSON] = await fetchJSONData();
    const [ohlcData, volumeData] = reformatOhlcvData(ohlcvData);

    const candlestickSeries = chart.addSeries(CandlestickSeries, {}, 0);
    const volumeSeries = chart.addSeries(HistogramSeries, {}, 1);
    const pft = volumeSeries.priceFormatter();
    candlestickSeries.setData(ohlcData);
    volumeSeries.setData(volumeData);
}


let MAIN_CHART: IChartApi;
let CHART_CONTAINER: HTMLDivElement;

window.addEventListener("load", () => {
    const chartContainerID = "chart-container";
    const container = document.getElementById(chartContainerID);
    if (!container) {
        console.error(`Could not find ${chartContainerID}`);
        throw new Error();
    }

    CHART_CONTAINER = container as HTMLDivElement;
    MAIN_CHART = setupChart(CHART_CONTAINER);
    render(MAIN_CHART);
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
