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
const TICKET_ENDPT = "/v3/reference/tickers"

func main() {
	bytes, err := os.ReadFile("API_KEY.secret")
	if err != nil {
		log.Fatalln(err)
	}
	content := strings.TrimSpace(string(bytes))
	API_KEY := strings.Split(content, "\n")[0]

	stock_ticker := "AAPL"
	mult := 2
	timespan := "hour"
	from := "2024-09-09"
	to := "2024-09-11"
	limit := 120
	target_url := fmt.Sprintf(
		"%s/v2/aggs/ticker/%s/range/%d/%s/%s/%s?apiKey=%s&limit=%d",
		BASE_URL, stock_ticker, mult, timespan, from, to, API_KEY, limit,
	)

	fmt.Println("Target URL: " + target_url + API_KEY)

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
	fmt.Println(root)

	fmt.Printf("      Ticker: %s\n", root.(Object)["ticker"].(string))
	fmt.Printf(" Query count: %d\n", int(root.(Object)["queryCount"].(float64)))
	count := int(root.(Object)["resultsCount"].(float64))
	fmt.Printf("Result count: %d\n", int(root.(Object)["resultsCount"].(float64)))
	fmt.Printf("    Adjusted: %t\n", root.(Object)["adjusted"].(bool))

	results := root.(Object)["results"].(Array)
	for i := range count {
		c := results[i].(Object)
		fmt.Printf("\t v: %d\n", int(c["v"].(float64)))
		fmt.Printf("\tvw: %f\n", c["vw"].(float64))
		fmt.Printf("\t o: %f\n", c["o"].(float64))
		fmt.Printf("\t o: %f\n", c["o"].(float64))
		fmt.Printf("\t c: %f\n", c["c"].(float64))
		fmt.Printf("\t h: %f\n", c["h"].(float64))
		fmt.Printf("\t l: %f\n", c["l"].(float64))
		fmt.Printf("\t t: %d\n", int64(c["t"].(float64)))
		fmt.Printf("\t n: %d\n", int(c["n"].(float64)))
	}
	fmt.Printf("      Status: %s\n", root.(Object)["status"].(string))
	fmt.Printf("  Request ID: %s\n", root.(Object)["request_id"].(string))
	fmt.Printf("        Count: %d\n", int(root.(Object)["resultsCount"].(float64)))
	// fmt.Printf("     Next URL: %s\n", root.(Object)["next_url"].(string))
}
