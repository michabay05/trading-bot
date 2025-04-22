package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
)

const BASE_URL = "https://api.polygon.io"

type CandleBar struct {
	open      float64
	close     float64
	low       float64
	high      float64
	volume    int
	timestamp uint64
}

func main() {
	bytes, err := os.ReadFile("API_KEY.secret")
	if err != nil {
		log.Fatalln(err)
	}
	content := strings.TrimSpace(string(bytes))
	API_KEY := strings.Split(content, "\n")[0]

	stock_ticker := "AAPL"
	mult := 5
	timespan := "hour"
	from := "2024-01-10"
	to := "2024-01-13"
	target_url := fmt.Sprintf(
		"%s/v2/aggs/ticker/%s/range/%d/%s/%s/%s?apiKey=%s",
		BASE_URL, stock_ticker, mult, timespan, from, to, API_KEY,
	)
	fmt.Println("Target URL: " + target_url)

	resp, err := http.Get(target_url)
	if err != nil {
		log.Fatalln(err)
	}
	defer resp.Body.Close()

	var root interface{}
	decoder := json.NewDecoder(resp.Body)
	type Object = map[string]interface{}
	type Array = []interface{}
	err = decoder.Decode(&root)
	if err != nil {
		log.Fatalln(err)
	}

	// TODO: use `json.Unmarshal()` instead of iterating through the array
	results := root.(Object)["results"].(Array)
	candles := []CandleBar{}
	for _, candle := range results {
		c := candle.(Object)

		cnd := CandleBar{
			low:       c["l"].(float64),
			open:      c["o"].(float64),
			close:     c["c"].(float64),
			high:      c["h"].(float64),
			timestamp: uint64(c["t"].(float64)),
			volume:    int(c["v"].(float64)),
		}
		candles = append(candles, cnd)
	}
}
