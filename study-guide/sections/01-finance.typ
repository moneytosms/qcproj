#import "../template.typ": *

= Part 1. Markets, Crypto and Volatility from Zero

== Markets and prices

A *market* is a place where buyers and sellers agree on a price. An *asset* is the thing traded (a share of a company, gold, a currency, a coin). The *price* is simply the last deal struck: if someone buys one unit at 100 and someone else buys at 101 a minute later, the price "moved" from 100 to 101. Prices move because new information or opinions change how much people are willing to pay.

An *exchange* is the company that runs the marketplace and matches buyers with sellers. Examples relevant here: *Bitstamp* (one of the oldest Bitcoin exchanges; we used its Bitcoin price history, Dec 2016 to Oct 2026) and *Binance* (the largest crypto exchange; we used it for nine more coins).

=== Stock markets versus crypto: when do they open?

#fig("/fig/market_hours.png", [Stocks trade in a fixed window on weekdays; crypto never closes.], width: 85%)

- *Traditional stock exchanges* (NYSE, NASDAQ) are open about 9:30 to 16:00 New York time, Monday to Friday, closed on holidays. Prices "jump" between the close and the next open because news arrives while it is shut.
- *Crypto markets* run *24 hours, 7 days a week, 365 days a year*. There is no closing bell. So a "day" in our data is just a chosen 24-hour window (we use calendar days, midnight to midnight UTC).
- Consequence for our project: weekends exist in crypto data. Trading is much quieter on weekends, so volatility is lower on Saturday and Sunday. Our v2 model adds "weekend" and "Monday" flags because of exactly this.

== Crypto in plain terms

*Bitcoin (BTC)* is a digital currency with no company or bank behind it. Ownership is recorded on a public ledger (the _blockchain_) kept by thousands of computers. Cryptography (digital signatures) proves you own coins without revealing a password. You do not need to understand the cryptography for this project: for us a coin is just *a price that moves every second*.

*Altcoins* are all the other coins: Ethereum (ETH), Solana (SOL), Dogecoin (DOGE), Litecoin (LTC), BNB, Cardano (ADA), Chainlink (LINK), Polkadot (DOT), Avalanche (AVAX). They are the "ten coins" experiment: if our model worked only for Bitcoin, that would be suspicious.

*USDT (Tether)* is a "stablecoin" meant to stay at about one US dollar. "BTCUSDT" on Binance means "the price of one Bitcoin measured in USDT". We use these pairs for the nine Binance coins.

*Klines / candles.* Exchanges publish price history as "candles": for each time slice (1 minute, 5 minutes, 1 day) you get the open, high, low and close price and the traded volume. We use 5-minute candles (Binance) and 1-minute prices (Bitstamp, grouped into 5-minute slices) and use only the closing price of each slice. A day has 24 × 12 = *288* five-minute slices, which is the "288" on slide 5.

*Why is crypto a good test case?* Its volatility is far higher than stocks, it trades non-stop (more data per day), and data is free and public.

== Returns: how much did the price change?

Raw prices are awkward (a \$1 move means something different at \$10 and at \$100,000), so we use *returns*, the percentage-like change.

*Simple return:* $(P_1 - P_0) / P_0$. Price 100 to 101 is +1%.

*Log return* (what we use): $r = ln(P_1 / P_0)$. For 100 to 101: $ln(1.01) = 0.00995$, nearly the same as 1% for small moves.

#math-box(title: "Why log returns?")[
  Log returns *add up over time*: the return over a day is the sum of the log returns of all its 5-minute slices. Percentage returns do not add up that cleanly. A +10% then −10% move does not return you to the start (110 × 0.9 = 99), but log returns of +0.0953 and −0.1054 are honest about it. Also, a log return can be any real number, which suits statistics.
]

== Volatility: how restless is the price?

*Volatility* is how much the price swings over a period, regardless of direction. Two days can end at exactly the same price and still feel completely different:

#fig("/fig/calm_vs_wild.png", [Same starting and ending price, very different journeys (illustration with random data).], width: 80%)

=== Realized volatility (RV): the measured, after-the-fact number

We never observe "true volatility", so we measure it from the intraday price path. Chop the day into $n$ slices, take each slice's log return $r_(t,i)$, *square* it, and add:

$ "RV"_t = sum_(i=1)^(n) r_(t,i)^2 $

#idea(title: "Why square the moves?")[
  Up-moves and down-moves both mean restlessness. Squaring makes both positive, so they add instead of cancelling. Squaring also makes big jumps count much more than small wiggles. A smooth day gives a tiny sum; a bumpy day, a big one.
]

*Worked example (verified).* Five consecutive log returns: +0.010, −0.020, +0.015, −0.005, +0.010. Squares: 0.0001, 0.0004, 0.000225, 0.000025, 0.0001. Sum: *RV = 0.00085*. Its square root, 0.0292, says "the typical day-size move was about 2.9%". (The sum of the plain returns is only 0.010, which shows a calm net result can hide a bumpy ride.)

*Why 288 slices and not just open and close?* Using only two prices throws away the path. With 288 prices we see the swings; more slices give a more accurate measurement of the day's true restlessness. Too-fine slices (every second) get polluted by tiny trading frictions, so 5 minutes is a standard compromise.

=== Why we use log(RV)

RV is always positive and has huge outliers (a crash day can be 100 times a quiet day). Taking the logarithm, $y_t = ln("RV"_t)$, makes the distribution roughly bell-shaped and the numbers manageable (in our data log RV ranges from about −11.7 to −2.3, with 98% of days between −10 and −4.3). Almost everything in the project (features, the four levels, the HAR model) works on $y_t$.

#fig("/fig/rv_history.png", [Real Bitcoin log RV, Dec 2016 to Oct 2026 (3,610 days). The orange line is the 30-day average: calm and stormy eras are clearly visible.], width: 95%)

== Volatility has memory (clustering)

The central empirical fact: *volatility clusters*. A turbulent day is usually followed by another turbulent day. Statisticians measure this with *autocorrelation*: the correlation between today's value and the value $k$ days ago.

#fig("/fig/memory_acf.png", [Autocorrelation of real Bitcoin log RV (computed by us from the data). Yesterday: 0.75; a week ago: 0.64; a month ago: 0.37; two months ago: 0.29. It decays slowly, called "long memory".], width: 75%)

Compare with returns themselves: today's return is nearly uncorrelated with yesterday's (you cannot easily guess the *direction*), but today's *size* of move is quite predictable. That is why forecasting volatility is realistic and forecasting price direction is not.

=== The HAR model (Corsi, 2009): the classical benchmark

HAR means *Heterogeneous AutoRegressive*. The idea: different traders act on different time scales (day traders, weekly traders, monthly investors), and each group contributes to volatility. So predict tomorrow's log RV as a weighted sum of three averages:

$ hat(y)_(t) = beta_0 + beta_d \, y_(t-1) + beta_w \, overline(y)_(t-7:t-1) + beta_m \, overline(y)_(t-30:t-1) $

where $y_(t-1)$ is yesterday's, $overline(y)_(t-7:t-1)$ the average of the previous 7 days, $overline(y)_(t-30:t-1)$ the average of the previous 30 days, and the $beta$'s are fitted by least squares. It is a simple linear regression, yet remarkably hard to beat.

#fig("/fig/har_windows.png", [The three look-back windows HAR uses. Our features are exactly these three, plus yesterday's return.], width: 85%)

*Our four input features* for each day (in code `history_features`): yesterday's log RV, the 7-day mean, the 30-day mean, and yesterday's return. The first 30 days of any dataset are dropped because they lack a full month of history. All features use only data *strictly before* the day being predicted (no peeking).

== Why anyone cares

- *Risk management:* banks and funds set how much money to hold in reserve from expected volatility ("Value at Risk").
- *Options pricing:* an option is insurance on a price; its cost depends mostly on expected volatility (the famous Black-Scholes formula). Expecting a stormy week makes insurance dearer.
- *Position sizing:* traders take smaller positions when volatility is high.
- Crypto is especially volatile, so a good forecast is worth more.

#note[Forecasting volatility is *not* forecasting whether Bitcoin goes up or down, and not a trading strategy. Our project never claims to make money.]

== Other finance words you may be asked about

#term("GARCH")[Generalized AutoRegressive Conditional Heteroskedasticity (Engle 1982, Bollerslev 1986). A classic model where today's variance equals a constant plus a share of yesterday's squared surprise plus a share of yesterday's variance. Another strong classical benchmark we raced against.]
#term("Multifractal / rough volatility")[Real volatility looks 'jagged' at every zoom level (a "rough" pattern; Gatheral et al. 2018), and its jaggedness varies in a structured way. The base paper checks whether generated data has this texture (Part 4).]
#term("Heavy tails")[Extreme price moves are much more common than a bell curve predicts. The paper's generated returns used Gaussian noise, so they lacked this; our rebuild noted the discrepancy.]
#term("QLIKE")[A standard error score for volatility forecasts, defined as $"RV"/hat(sigma)^2 - ln("RV"/hat(sigma)^2) - 1$; it punishes under-forecasting storms more than over-forecasting (Patton 2011).]
#term("Out-of-sample")[Data a model never saw while training. Only out-of-sample results mean anything.]
