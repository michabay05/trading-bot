module talib;

enum RetCode : int (int val)
{
    /* No error */
    TA_SUCCESS = 0,
    /* TA_Initialize was not sucessfully called */
    TA_LIB_NOT_INITIALIZE = 1,
    /* A parameter is out of range */
    TA_BAD_PARAM = 2,
    /* Possibly out-of-memory */
    TA_ALLOC_ERR = 3,
    TA_GROUP_NOT_FOUND = 4,
    TA_FUNC_NOT_FOUND = 5,
    TA_INVALID_HANDLE = 6,
    TA_INVALID_PARAM_HOLDER = 7,
    TA_INVALID_PARAM_HOLDER_TYPE = 8,
    TA_INVALID_PARAM_FUNCTION = 9,
    TA_INPUT_NOT_ALL_INITIALIZE = 10,
    TA_OUTPUT_NOT_ALL_INITIALIZE = 11,
    TA_OUT_OF_RANGE_START_INDEX = 12,
    TA_OUT_OF_RANGE_END_INDEX = 13,
    TA_INVALID_LIST_TYPE = 14,
    TA_BAD_OBJECT = 15,
    TA_NOT_SUPPORTED = 16,
    TA_INTERNAL_ERROR = 5000,
    TA_UNKNOWN_ERR = 0xFFFF
}

extern fn void initialize() @extern("TA_Initialize");

extern fn RetCode sma(
    int startIdx,
    int endIdx,
    double* inReal,
    int optInTimePeriod, /* From 2 to 100000 */
    int *outBegIdx,
    int *outNBElement,
    double* outReal
) @extern("TA_SMA");
extern fn int sma_lookback(int optInTimePeriod) @extern("TA_SMA_Lookback");

extern fn RetCode ema(
    int startIdx,
    int endIdx,
    double* inReal,
    int optInTimePeriod, /* From 2 to 100000 */
    int *outBegIdx,
    int *outNBElement,
    double* outReal
) @extern("TA_EMA");
extern fn int ema_lookback(int optInTimePeriod) @extern("TA_EMA_Lookback");
