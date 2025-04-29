package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"
)

const BASE_URL = "https://api.polygon.io"

type Candle struct {
	open      float64
	high      float64
	low       float64
	close     float64
	volume    int
	timestamp int64
}

func (cnd *Candle) String() string {
	timestamp := timestampToDateTime(cnd.timestamp)
	return fmt.Sprintf("Candle {\n   open: %.2f\n   high: %.2f\n   low: %.2f\n   close: %.2f\n   volume: %d\n   timestamp: %s\n}",
		cnd.open, cnd.high, cnd.low, cnd.close, cnd.volume, timestamp)
}

func (cnd *Candle) series_val(series string) (float64, error) {
	switch series {
	case "open":
		return cnd.open, nil
	case "close":
		return cnd.close, nil
	case "low":
		return cnd.low, nil
	case "high":
		return cnd.high, nil
	default:
		return -1, errors.New("")
	}
}

type IndicatorValues struct {
	timestamp int64
	value     float64
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
	// Format: YYYY-MM-DD
	timestamp string
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

func httpGetJSON(target_url string) Object {
	resp, err := http.Get(target_url)
	if err != nil {
		log.Fatalln(err)
	}
	defer resp.Body.Close()

	var root Object
	decoder := json.NewDecoder(resp.Body)
	err = decoder.Decode(&root)
	if err != nil {
		log.Fatalln(err)
	}
	return root
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

	root := httpGetJSON(target_url)
	// TODO: use `json.Unmarshal()` instead of iterating through the array
	results := root["results"].(Array)
	candles := []Candle{}
	for _, candle := range results {
		c := candle.(Object)

		cnd := Candle{
			low:       c["l"].(float64),
			open:      c["o"].(float64),
			close:     c["c"].(float64),
			high:      c["h"].(float64),
			timestamp: int64(c["t"].(float64)),
			volume:    int(c["v"].(float64)),
		}
		candles = append(candles, cnd)
	}
	return candles
}

func getIndicator(API_KEY string, kind string, ticker string, opt IndicatorOption) []IndicatorValues {
	target_url := fmt.Sprintf(
		"%s/v1/indicators/%s/%s?timestamp=%s&timespan=%s&series_type=%s&window=%d&apiKey=%s",
		BASE_URL, kind, ticker, opt.timestamp, opt.timespan, opt.series_type,
		opt.window, API_KEY,
	)

	root := httpGetJSON(target_url)
	values := root["results"].(Object)["values"].(Array)

	ind_vals := []IndicatorValues{}
	for _, val := range values {
		v := val.(Object)
		ind_vals = append(ind_vals, IndicatorValues{
			timestamp: int64(v["timestamp"].(float64)),
			value:     v["value"].(float64),
		})
	}
	return ind_vals
}

// Exports an array of candles into a CSV file
func exportCandles(candles []Candle) error {
	sb := strings.Builder{}
	_, err := sb.WriteString(",date,open,high,low,close,volume\n")
	if err != nil {
		return err
	}
	for i, c := range candles {
		date := timestampToDateTime(c.timestamp)
		line := fmt.Sprintf(
			"%d,%s,%.4f,%.4f,%.4f,%.4f,%d",
			i, date, c.open, c.high, c.low, c.close, c.volume)
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
	candle_opt := CandleOption{
		start:    "2025-04-23 15:15:00",
		end:      "2025-04-24 15:15:00",
		mult:     15,
		timespan: "minute",
	}
	candles := getCandles(API_KEY, ticker, candle_opt)
	fmt.Println(candle_opt.String())
	series_s := []string{ "close", "high", "open" }
	for _, series := range series_s {
		ind := highestCandle(candles, series, len(candles))
		fmt.Printf("Highest candles by %s: %s\n---------------\n", series, candles[ind].String())
	}


	// sma_opt := IndicatorOption{
	// 	timestamp:   "2025-04-10",
	// 	timespan:    "hour",
	// 	window:      10,
	// 	series_type: "close",
	// }
	// sma10 := getIndicator(API_KEY, "sma", ticker, sma_opt)
	// sma_opt.window = 30
	// sma30 := getIndicator(API_KEY, "sma", ticker, sma_opt)
}
