package main

import (
	"encoding/csv"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
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
	ticker   string
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

	candles := root.Results
	if len(root.NextURL) != 0 {
		data, err := httpGet_v2(root.NextURL + "?apiKey=" + API_KEY)
		if err != nil {
			log.Fatal(err)
		}
		var root2 CandleResponse
		json.Unmarshal(data, &root2)
		candles = append(candles, root2.Results...)

		if len(root2.NextURL) != 0 {
			println("--------")
			println(root2.NextURL)
			println("TODO: More values to collect")
			println("--------")
			log.Fatalln("Fix TODO here")
		}
	}

	return candles
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
}

func getHistoricalCandles(API_KEY string, opt CandleOption) []Candle {
	start_unix, err := dateTimeToTimestamp(opt.start)
	if err != nil {
		log.Fatalln(err)
	}
	end_unix, err := dateTimeToTimestamp(opt.end)
	if err != nil {
		log.Fatalln(err)
	}

	const QUERY_LIMIT int = 1150
	candles := []Candle{}
	// Number of candles we can get in one request based on query limit and multiplier
	CANDLES_PER_REQ := QUERY_LIMIT * opt.mult
	// Total minutes of data we can get per request
	MINS_PER_REQ := CANDLES_PER_REQ
	// Convert minutes to milliseconds for timestamp calculations
	MS_PER_REQ := MINS_PER_REQ * 60 * 1000

	curr_start := start_unix
	requestCount := 0
	for curr_start < end_unix {
		curr_end := min(curr_start + int64(MS_PER_REQ), end_unix)

		opt.start = timestampToDateTime(curr_start)
		opt.end = timestampToDateTime(curr_end)
		batch := getCandles(API_KEY, opt.ticker, opt)
		candles = append(candles, batch...)

		log.Printf("Query complete: %s to %s", opt.start, opt.end)

		curr_start = curr_end
		requestCount++

		if requestCount%2 == 0 {
			log.Println("Waiting 60 seconds before next request...")
			time.Sleep(60 * time.Second)
		}
	}

	return candles
}

// Exports an array of candles into a CSV file
func exportCandles(candles []Candle, opt CandleOption) error {
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

	start_unix, err := dateTimeToTimestamp(opt.start)
	if err != nil {
		log.Fatalln(err)
	}
	end_unix, err := dateTimeToTimestamp(opt.end)
	if err != nil {
		log.Fatalln(err)
	}
	outPath := fmt.Sprintf(
		"ohlcv-%s%s-%s%s-%d%s-%s.csv",
		time.UnixMilli(start_unix).Format("Jan"),
		time.UnixMilli(start_unix).Format("06"),
		time.UnixMilli(end_unix).Format("Jan"),
		time.UnixMilli(end_unix).Format("06"),
		opt.mult,
		opt.timespan,
		opt.ticker,
	)
	os.WriteFile(outPath, []byte(sb.String()), 0644)
	return nil
}

func importCandles(filepath string) ([]Candle, error) {
	candles := []Candle{}
	f, err := os.Open(filepath)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	lines, err := csv.NewReader(f).ReadAll()
	if err != nil {
		return nil, err
	}

	for i := range len(lines) {
		// First line is a header
		if i == 0 {
			continue
		}
		line := lines[i]

		// i, date, c.Open, c.High, c.Low, c.Close, c.Volume
		unixTimestamp, err := dateTimeToTimestamp(line[1])
		if err != nil {
			return nil, err
		}
		open, err := strconv.ParseFloat(line[2], 64)
		if err != nil {
			return nil, err
		}
		high, err := strconv.ParseFloat(line[3], 64)
		if err != nil {
			return nil, err
		}
		low, err := strconv.ParseFloat(line[4], 64)
		if err != nil {
			return nil, err
		}
		close, err := strconv.ParseFloat(line[5], 64)
		if err != nil {
			return nil, err
		}
		volume, err := strconv.ParseFloat(line[6], 64)
		if err != nil {
			return nil, err
		}

		candles = append(candles, Candle{
			Open:      open,
			High:      high,
			Low:       low,
			Close:     close,
			Volume:    volume,
			Timestamp: unixTimestamp,
		})
	}

	return candles, nil
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

func candleEqual(a, b Candle) bool {
	if a.Open != b.Open {
		return false
	}
	if a.Close != b.Close {
		return false
	}
	if a.High != b.High {
		return false
	}
	if a.Low != b.Low {
		return false
	}
	if a.Close != b.Close {
		return false
	}
	if a.Volume != b.Volume {
		return false
	}
	if a.Timestamp != b.Timestamp {
		return false
	}
	return true
}

func main() {
	bytes, err := os.ReadFile("API_KEY.secret")
	if err != nil {
		log.Fatalln(err)
	}
	API_KEY := strings.TrimSpace(string(bytes))

	opt := CandleOption{
		start:    "2024-01-01 10:00:00",
		end:      "2025-04-30 16:00:00",
		mult:     5,
		timespan: "minute",
		ticker:   "SPY",
	}

	candles := getHistoricalCandles(API_KEY, opt)
	err = exportCandles(candles, opt)
	if err != nil {
		log.Fatalln(err)
	}
}
