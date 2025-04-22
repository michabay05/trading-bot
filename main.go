package main

import (
	"encoding/json"
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
	close     float64
	low       float64
	high      float64
	volume    int
	timestamp int64
}

type Object = map[string]interface{}
type Array = []interface{}

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

func getCandles(API_KEY string, stock_ticker string) []Candle {
	mult := 5
	timespan := "hour"
	from := "2024-01-10"
	to := "2024-01-13"
	target_url := fmt.Sprintf(
		"%s/v2/aggs/ticker/%s/range/%d/%s/%s/%s?apiKey=%s",
		BASE_URL, stock_ticker, mult, timespan, from, to, API_KEY,
	)
	fmt.Println("Target URL: " + target_url)

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

func getRSIs(API_KEY string) {
	stock_ticker := "SPY"
	timestamp := "2025-04-21"
	timespan := "hour"
	series_type := "close"
	window := 14
	target_url := fmt.Sprintf(
		"%s/v1/indicators/rsi/%s?timestamp=%s&timespan=%s&series_type=%s&window=%d&apiKey=%s",
		BASE_URL, stock_ticker, timestamp, timespan, series_type, window, API_KEY,
	)
	fmt.Println("Target URL: " + target_url)

	root := httpGetJSON(target_url)
	values := root["results"].(Object)["values"].(Array)

	for i, rsiVals := range values {
		val := rsiVals.(Object)
		fmt.Printf("values[%d] = {\n", i)
		timestamp := int64(val["timestamp"].(float64))
		fmt.Printf("    timestamp: %d (%s)\n", timestamp, timestampToDate(timestamp))
		fmt.Printf("        value: %f\n", val["value"].(float64))
		fmt.Println("}")
	}
}

func timestampToDate(timestamp int64) string {
	t := time.UnixMilli(timestamp)
	return t.Format(time.DateTime)
}

func main() {
	bytes, err := os.ReadFile("API_KEY.secret")
	if err != nil {
		log.Fatalln(err)
	}
	API_KEY := strings.TrimSpace(string(bytes))

	stock_ticker := "AAPL"
	timestamp := "2025-04-21"
	timespan := "day"
	window := 50
	series_type := "close"
	target_url := fmt.Sprintf(
		"%s/v1/indicators/ema/%s?timestamp=%s&timespan=%s&window=%d&series_type=%s&apiKey=%s",
		BASE_URL, stock_ticker, timestamp, timespan, window, series_type, API_KEY,
	)
	fmt.Println("Target URL: " + target_url)

	// TODO: SMA, EMA, and RSI are very similar. Create a simpler way to access them
	root := httpGetJSON(target_url)
	values := root["results"].(Object)["values"].(Array)

	for i, emaVals := range values {
		val := emaVals.(Object)
		fmt.Printf("values[%d] = {\n", i)
		timestamp := int64(val["timestamp"].(float64))
		fmt.Printf("    timestamp: %d (%s)\n", timestamp, timestampToDate(timestamp))
		fmt.Printf("        value: %f\n", val["value"].(float64))
		fmt.Println("}")
	}
}
