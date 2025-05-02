package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"
)

const BASE_URL = "https://api.polygon.io"

type Candle struct {
	Open      float64 `json:"o"`
	High      float64 `json:"h"`
	Low       float64 `json:"l"`
	Close     float64 `json:"c"`
	Volume    float64 `json:"v"`
	Timestamp int64   `json:"t"`
}

func (cnd *Candle) String() string {
	timestamp := timestampToDateTime(cnd.Timestamp)
	return fmt.Sprintf("Candle {\n   open: %.2f\n   high: %.2f\n   low: %.2f\n   close: %.2f\n   volume: %.1f\n   timestamp: %s\n}",
		cnd.Open, cnd.High, cnd.Low, cnd.Close, cnd.Volume, timestamp)
}

func (cnd *Candle) series_val(series string) (float64, error) {
	switch series {
	case "open":
		return cnd.Open, nil
	case "close":
		return cnd.Close, nil
	case "low":
		return cnd.Low, nil
	case "high":
		return cnd.High, nil
	default:
		return -1, errors.New("")
	}
}

type CandleResponse struct {
	Ticker       string   `json:"ticker"`
	QueryCount   int      `json:"queryCount"`
	ResultsCount int      `json:"resultsCount"`
	Status       string   `json:"status"`
	Results      []Candle `json:"results,omitempty"`
	NextURL      string   `json:"next_url,omitempty"`
}

// TODO: refactor this to use json stuff
type IndicatorResponse struct {
	NextURL string `json:"next_url,omitempty"`
	Status  string `json:"status"`
	Results struct {
		Values []IndicatorValues `json:"values"`
	} `json:"results"`
}

type IndicatorValues struct {
	Timestamp int64   `json:"timestamp,omitempty"`
	Value     float64 `json:"value,omitempty"`
}

type CandleOption struct {
	start    string
	end      string
	mult     int
	timespan string
}

func (co *CandleOption) String() string {
	return fmt.Sprintf("CandleOption{\n   start: %s\n   end: %s\n   mult: %d\n   timespan: %s\n}",
		co.start, co.end, co.mult, co.timespan)
}

type IndicatorOption struct {
	// Format: Unix millis
	timestampLTE int64
	// Possible values:
	// ["second", "minute", "hour", "day", "week", "month", "year"]
	timespan string
	// Number of candles to consider
	window int
	// Possible values: ["open", "close", "high", "low"]
	series_type string
}

type Object = map[string]any // any ~ interface{}
type Array = []any           // any ~ interface{}

func httpGet_v2(target_url string) ([]byte, error) {
	resp, err := http.Get(target_url)
	if err != nil {
		log.Fatalln(err)
	}
	defer resp.Body.Close()

	return io.ReadAll(resp.Body)
}

func getCandles(API_KEY string, stock_ticker string, opt CandleOption) []Candle {
	start_unix, err := dateTimeToTimestamp(opt.start)
	if err != nil {
		log.Println("Start string: " + opt.start)
		log.Fatalln("getCandles() => Invalid start string")
	}

	end_unix, err := dateTimeToTimestamp(opt.end)
	if err != nil {
		log.Println("End string: " + opt.end)
		log.Fatalln("getCandles() => Invalid end string")
	}

	target_url := fmt.Sprintf(
		"%s/v2/aggs/ticker/%s/range/%d/%s/%d/%d?apiKey=%s",
		BASE_URL, stock_ticker, opt.mult, opt.timespan, start_unix, end_unix, API_KEY,
	)
	fmt.Println("Target URL: " + target_url)
	fmt.Println("-----------")

	data, err := httpGet_v2(target_url)
	if err != nil {
		log.Fatal(err)
	}
	var root CandleResponse
	json.Unmarshal(data, &root)

	return root.Results
}

func getIndicator(API_KEY string, kind string, ticker string, opt IndicatorOption) []IndicatorValues {
	target_url := fmt.Sprintf(
		"%s/v1/indicators/%s/%s?timestamp.lte=%d&timespan=%s&series_type=%s&window=%d&apiKey=%s",
		BASE_URL, kind, ticker, opt.timestampLTE, opt.timespan, opt.series_type,
		opt.window, API_KEY,
	)

	data, err := httpGet_v2(target_url)
	if err != nil {
		log.Fatal(err)
	}
	var root IndicatorResponse
	json.Unmarshal(data, &root)
	return root.Results.Values

	// var root Object
	// values := root["results"].(Object)["values"].(Array)

	// ind_vals := []IndicatorValues{}
	// for _, val := range values {
	// 	v := val.(Object)
	// 	ind_vals = append(ind_vals, IndicatorValues{
	// 		timestamp: int64(v["timestamp"].(float64)),
	// 		value:     v["value"].(float64),
	// 	})
	// }

	// max_limit := root["queryCount"].(int64)
	// val_count := root["resultsCount"].(int64)

	// if val_count > max_limit {
	// 	log.Fatal("Shut up")
	// }

	// if int(val_count) != len(values) {
	// 	log.Fatal("Shut up v2")
	// }
	// fmt.Println("yessah")

	// return ind_vals
}

// Exports an array of candles into a CSV file
func exportCandles(candles []Candle) error {
	sb := strings.Builder{}
	_, err := sb.WriteString(",date,open,high,low,close,volume\n")
	if err != nil {
		return err
	}
	for i, c := range candles {
		date := timestampToDateTime(c.Timestamp)
		line := fmt.Sprintf(
			"%d,%s,%.4f,%.4f,%.4f,%.4f,%.0f",
			i, date, c.Open, c.High, c.Low, c.Close, c.Volume)
		_, err := sb.WriteString(line + "\n")
		if err != nil {
			return err
		}
	}

	// Default output path: "ohlcv.csv"
	os.WriteFile("ohlcv.csv", []byte(sb.String()), 0644)
	return nil
}

func highestCandle(candles []Candle, series string, n int) int {
	max := -1.0
	max_ind := -1
	i := len(candles) - n
	for i < len(candles) {
		val, err := candles[i].series_val(series)
		if err != nil {
			log.Fatalln(err.Error())
		}
		if val > max {
			max_ind = i
			max = val
		}
		i++
	}
	return max_ind
}

func timestampToDateTime(timestamp int64) string {
	t := time.UnixMilli(timestamp)
	return t.In(time.Local).Format(time.DateTime)
}

func dateTimeToTimestamp(datetime string) (int64, error) {
	// time.DateTime = "2006-01-02 15:04:05"
	parsed, err := time.ParseInLocation(time.DateTime, datetime, time.Local)
	if err != nil {
		return -1, err
	}
	return parsed.UnixMilli(), nil
}

func main() {
	bytes, err := os.ReadFile("API_KEY.secret")
	if err != nil {
		log.Fatalln(err)
	}
	API_KEY := strings.TrimSpace(string(bytes))

	ticker := "SPY"

	unix_ts, err := dateTimeToTimestamp("2025-04-13 10:00:00")
	println(unix_ts)
	if err != nil {
		log.Fatalln(err)
	}
	ind_opt := IndicatorOption{
		timestampLTE: unix_ts,
		timespan:     "minute",
		window:       8,
		series_type:  "close",
	}
	sma8 := getIndicator(API_KEY, "sma", ticker, ind_opt)
	ind_opt.window = 21
	// sma21 := getIndicator(API_KEY, "sma", ticker, ind_opt)
	fmt.Println(sma8)
	// fmt.Println(sma21)

	// candle_opt := CandleOption{
	// 	start:    "2025-04-20 15:15:00",
	// 	end:      "2025-04-24 15:15:00",
	// 	mult:     1,
	// 	timespan: "day",
	// }
	// candles := getCandles(API_KEY, ticker, candle_opt)
	// for _, candle := range candles {
	// 	fmt.Println(candle.String())
	// }
	// series_s := []string{ "close", "high", "open" }
	// for _, series := range series_s {
	// 	ind := highestCandle(candles, series, len(candles))
	// 	fmt.Printf("Highest candles by %s: %s\n---------------\n", series, candles[ind].String())
	// }
}
