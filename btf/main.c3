import std::io;
import std::math::random;
import std::collections::list;
import std::core::mem::allocator;
import std::io::file;

import talib;

// TODO:
//  - [ ] Represent candles
//  - [ ] Represent strategies
//  - [ ] Track progress of portfolio

faultdef PEEKED_TOO_FAR, NO_SUCH_HEADER, UNEQUAL_ROWS, UNKNONW_HEADER;

union ValueList
{
    List{String} strs;
    List{double} flts;
}

enum ValueListType : int (String desc)
{
    VLT_STRING = "string",
    VLT_DOUBLE = "double"
}

struct DataCol
{
    String header;
    ValueListType type;
    ValueList as;
}

fn usz DataCol.rows(DataCol *self)
{
    switch (self.type) {
        case VLT_STRING:
            return self.as.strs.len();
        case VLT_DOUBLE:
            return self.as.flts.len();
    }
}

fn void DataCol.print_value(DataCol *self, usz i)
{
    switch (self.type) {
        case VLT_STRING:
            io::printf("\"%s\"", self.as.strs[i]);
        case VLT_DOUBLE:
            io::printf("%.2f", self.as.flts[i]);
    }
}

struct Data
{
    List{DataCol} cols;
    usz rows_count, cols_count;
}

fn DataCol*? Data.get_col(Data *self, String hdr)
{
    for (usz i = 0; i < self.cols_count; i++) {
        DataCol *c = &self.cols[i];
        if (c.header == hdr) return c;
    }
    return UNKNONW_HEADER?;
}

fn void Data.new_col(Data *self, String hdr, ValueListType vlt)
{
    self.cols.push({
        .header = hdr,
        .type = vlt,
    });
    self.cols_count++;
}

fn void Data.add_value(Data *self, int c, String s)
{
    assert(c < self.cols_count, "Column limit exceeded");
    DataCol *col = &self.cols[c];
    switch (col.type) {
        case VLT_STRING:
            col.as.strs.push(s);
        case VLT_DOUBLE:
            col.as.flts.push(s.to_double()!!);
    }
}

fn void Data.dump_as_json(Data *self)
{
    foreach (DataCol c : self.cols) {
        io::print("{ ");
        io::printf("\"header\": \"%s\", ", c.header);
        io::printf("\"type\": \"%s\", ", c.type.desc);
        io::printf("\"values\": [ ");
        for (usz i = 0; i < self.rows_count; i++) {
            c.print_value(i);
            if (i < self.rows_count - 1) {
                io::print(", ");
            }
        }
        io::print("]");
        io::printn(" }");
    }
}

fn void Data.dump_as_csv(Data *self)
{
    for (int r = -1; r < self.rows_count; r++) {
        for (usz c = 0; c < self.cols_count; c++) {
            DataCol *col = &self.cols[c];
            if (r == -1) {
                io::print(col.header);
            } else {
                col.print_value(r);
            }
            if (c < self.cols_count - 1) {
                io::print(",");
            }
        }
        io::printn();
    }
}

fn void? Data.count_rows(Data *self)
{
    usz row_count = self.cols[0].rows();
    for (usz i = 1; i < self.cols_count; i++) {
        DataCol c = self.cols[i];
        if (c.rows() != row_count) {
            return UNEQUAL_ROWS?;
        }
    }
    self.rows_count = row_count;
}

fn void? Data.parse_csv(Data *self, String buf)
{
    int row = -1;
    int col = 0;
    int i = 0;
    while (i < buf.len) {
        char c = peek(buf, i)!;
        switch (c) {
            case '\n': {
                row++;
                col = 0;
                i++;
            }
            case ',': {
                col++;
                i++;
            }
            default: {
                String s = consume(buf, &i)!;
                if (row == -1) {
                    self.new_col(s, col == 0 ? VLT_STRING : VLT_DOUBLE);
                } else {
                    self.add_value(col, s);
                }
            }
        }
    }

    self.count_rows()!;
}

<*
    @require 1 <= i, i < arr1.len
    @require arr1.len == arr2.len : "arr1 should equal arr2"
*>
fn bool crossover(float[] arr1, float[] arr2, uint i)
{
    return arr1[i-1] < arr2[i-1] && arr1[i] > arr2[i];
}

fn char? peek(String buf, int i)
{
    if (i > buf.len) return PEEKED_TOO_FAR?;
    return buf[i];
}

fn String? consume(String buf, int *i)
{
    int start = *i;
    while (*i < buf.len) {
        char c = peek(buf, *i)!;
        if (c == ',' || c == '\n') break;
        (*i)++;
    }
    return buf[start..(*i)-1];
}

fn int main()
{
    const String PATH = "test.csv";
    File? f = file::open(PATH, "r");
    defer (void)f.close();
    if (catch e = f) {
        io::eprintfn("ERROR: %s", e);
        return 1;
    }
    usz fsz = file::get_size(PATH)!!;
    String buf = (String) mem::temp_array(char, fsz);
    f.read(buf)!!;

    Data data;
    data.parse_csv(buf)!!;
    io::printfn("Data: %d rows x %d cols", data.rows_count, data.cols_count);

    talib::initialize();
    DataCol *close_col = data.get_col("close")!!;
    assert(close_col.type == VLT_DOUBLE);

    double[] in = close_col.as.flts.array_view();

    // Source: https://www.programmersought.com/article/21547964545/
    int opt_period = 7;
    int start_idx = 0;
    int end_idx = in.len - 1;
    int lookback = talib::ema_lookback(opt_period);
    io::printn(lookback);
    int temp = max(lookback, start_idx);
    int out_alloc_size @noinit;
    if (temp > end_idx) {
        out_alloc_size = 0;
    } else {
        out_alloc_size = end_idx - temp + 1;
    }

    double[] out = mem::temp_array(double, out_alloc_size);
    int out_beg_idx, out_nb_el;
    RetCode ret = talib::ema(
        start_idx, end_idx, in,
        opt_period,
        &out_beg_idx, &out_nb_el, out
    );

    io::printn(out);
    io::printfn("Out begin index: %d", out_beg_idx);
    io::printfn("Out # of elements: %d", out_nb_el);
    io::printfn("Out length: %d", out.len);
    io::printfn("Return code: %s", ret);

    String ema_hdr = "EMA_1";
    data.new_col(ema_hdr, VLT_DOUBLE);
    DataCol *ema_col = data.get_col(ema_hdr)!!;
    ema_col.as.flts.tinit(in.len);
    for (int i = 0; i <= out_beg_idx; i++) {
        ema_col.as.flts.push(-1.0);
    }
    ema_col.as.flts.add_array(out);
    data.dump_as_csv();

    return 0;
}
