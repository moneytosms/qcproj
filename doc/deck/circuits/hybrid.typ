#import "style.typ": *
#show: setup
#set text(size: 26pt)
$ p_"hybrid" = "softmax"( #text(fill: class)[$log p_"HAR"$] + #text(fill: quant)[$gamma (q_"circuit" - 1/4)$] ) $
