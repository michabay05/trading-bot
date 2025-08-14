import {
    createChart, ColorType, LineStyle, CrosshairMode, CandlestickSeries,
    HistogramSeries, LineSeries,
    type ChartOptions, type DeepPartial, type OhlcData, type HistogramData,
    type IChartApi, type UTCTimestamp, type ISeriesApi,
    type LineData, type WhitespaceData,
    LineType,
    LastPriceAnimationMode
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

interface _ISymbolsInfo {
    symbols: string[];
}

interface _ILastUpdate {
    symbol: string;
    new_candles: _IOhlcvData[];
    new_ind_values: number[];
}

type _LWMultIndicatorData = { [name: string]:  ISeriesApi<"Line"> };
type _LWIndicatorData = LineData | WhitespaceData;

async function fetchInfo(): Promise<_ISymbolsInfo> {
    const symbolsResp = await fetch("info.json");
    return symbolsResp.json();
}

async function fetchLastUpdate(symbol: string): Promise<_ILastUpdate> {
    const updateResp = await fetch("updates.json");
    console.log(updateResp);
    const updateJSON = await updateResp.json();
    return updateJSON[symbol];
}

async function fetchJSONData(symbol: string): Promise<[_IOhlcvData[], _IIndsRenderData[]]> {
    const symbolInfoResp = await fetch(`${symbol}.json`);
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

function reformatOhlcvData(ohlcvData: _IOhlcvData[], start: number = 0): [OhlcData[], HistogramData[]] {
    let ohlcData: OhlcData[] = [];
    let volData: HistogramData[] = [];
    for (let i = start; i < ohlcvData.length; i++) {
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

function reformatIndicatorData(indicatorData: _IIndsRenderData[]): _LWIndicatorData[][] {
    const output: _LWIndicatorData[][] = [];
    for (const ind of indicatorData) {
        const indData: _LWIndicatorData[] = [];
        for (let j = 0; j < ind.data.length; j++) {
            indData.push({
                time: ind.data[j].time as UTCTimestamp,
                value: ind.data[j].value,
            });
        }
        output.push(indData);
    }
    return output;
}

async function visualizeData(
    ohlcvData: _IOhlcvData[], indicatorData: _IIndsRenderData[],
    candleSeries: ISeriesApi<"Candlestick">, volumeSeries: ISeriesApi<"Histogram">,
    multIndSeries: _LWMultIndicatorData
): Promise<void> {
    const [ohlcData, volumeData] = reformatOhlcvData(ohlcvData);
    candleSeries.setData(ohlcData);
    volumeSeries.setData(volumeData);

    if (indicatorData.length != Object.keys(multIndSeries).length) {
        console.error(
            `indicatorData.length (${indicatorData.length}) != lineSeriesArr.length(${multIndSeries.length})`);
        throw Error();
    }

    const multipleIndData = reformatIndicatorData(indicatorData);
    for (let i = 0; i < indicatorData.length; i++) {
        // TODO: make sure that overlaid data is placed in pane 0 and the others in pane 3.
        //       probably through some kind of assert
        multIndSeries[indicatorData[i].name].setData(multipleIndData[i]);
    }
}


let MAIN_CHART: IChartApi;
let CHART_CONTAINER: HTMLDivElement;

window.addEventListener("load", async () => {
    const containerDivID: string = "chart-container";
    const containerDiv = document.getElementById(containerDivID);
    if (!containerDiv) {
        console.error(`Could not find ${containerDivID}`);
        throw new Error();
    }

    const symbolDropdownID: string = "symbol-dropdown";
    const symbolDropdown = document.getElementById(symbolDropdownID) as HTMLSelectElement;
    if (!symbolDropdown) {
        console.error(`Could not find ${symbolDropdownID}`);
        throw new Error();
    }

    const symbolSubmitID: string = "symbol-submit-btn";
    const symbolSubmitBtn = document.getElementById(symbolSubmitID) as HTMLButtonElement;
    if (!symbolSubmitBtn) {
        console.error(`Could not find ${symbolSubmitID}`);
        throw new Error();
    }

    const updateDataBtnID: string = "update-data-btn";
    const updateDataBtn = document.getElementById(updateDataBtnID) as HTMLButtonElement;
    if (!symbolSubmitBtn) {
        console.error(`Could not find ${updateDataBtnID}`);
        throw new Error();
    }

    // Set global variables
    CHART_CONTAINER = containerDiv as HTMLDivElement;
    MAIN_CHART = setupChart(CHART_CONTAINER);

    const info = await fetchInfo();
    for (const symbol of info.symbols) {
        const option = document.createElement("option");
        option.value = symbol;
        option.innerText = symbol;
        symbolDropdown.appendChild(option);
    }

    // Pane indicies:
    //    - 0 for Candles and overlaid indicators like EMA
    //    - 1 for Candle volume
    //    - 2 for Non-overlaid indicators like RSI

    const defaultSymbol = symbolDropdown.options[0].value;
    let [ohlcvData, indicatorData] = await fetchJSONData(defaultSymbol);
    const cndSeries: ISeriesApi<"Candlestick"> = MAIN_CHART.addSeries(CandlestickSeries, {}, 0);
    const volSeries: ISeriesApi<"Histogram"> = MAIN_CHART.addSeries(HistogramSeries, {}, 1);
    const multIndSeries: _LWMultIndicatorData = {};
    for (const ind of indicatorData) {
        const paneIndex = ind.overlay ? 0 : 2;
        const lineSeries = MAIN_CHART.addSeries(LineSeries, {
            color: ind.color,
            lineType: LineType.Simple,
            lastPriceAnimation: LastPriceAnimationMode.OnDataUpdate
        }, paneIndex);
        multIndSeries[ind.name] = lineSeries;
    }

    console.log(`Default symbol: ${defaultSymbol}`);
    await visualizeData(ohlcvData, indicatorData, cndSeries, volSeries, multIndSeries);

    symbolSubmitBtn.addEventListener("click", async () => {
        const symbol: string = symbolDropdown.value;
        [ohlcvData, indicatorData] = await fetchJSONData(symbol);
        console.log(`Rendering ${symbol}...`)
        await visualizeData(ohlcvData, indicatorData, cndSeries, volSeries, multIndSeries);
    });

    updateDataBtn.addEventListener("click", async () => {
        const symbol: string = symbolDropdown.value;
        const lastUpdate: _ILastUpdate = await fetchLastUpdate(symbol);
        const [lastOhclv, lastVolume] = reformatOhlcvData(
            lastUpdate.new_candles, lastUpdate.new_candles.length - 1
        );
        cndSeries.update(lastOhclv[0]);
        volSeries.update(lastVolume[0]);

        for (const [ind_name, ind_val] of Object.entries(lastUpdate.new_ind_values)) {
            multIndSeries[ind_name].update({
                time: lastOhclv[0].time,
                value: ind_val
            });
        }
    });
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
