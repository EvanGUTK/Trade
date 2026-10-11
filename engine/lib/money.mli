(** Exact money arithmetic in integer micro-dollars.

    Convention (docs/ARCHITECTURE.md §3): every monetary amount that crosses the
    engine boundary is an [int64] count of micro-dollars, where
    [1 USD = 1_000_000] micro-dollars. Quantities use the same scale as integer
    micro-shares ([1 share = 1_000_000] micro-shares). No float is ever used for
    money inside the engine.

    [t] is abstract so that raw [Int64] arithmetic cannot leak in: every
    operation here is overflow-checked. *)

type t
(** A signed amount of money in micro-dollars. *)

exception Overflow
(** Raised by [add], [sub], [neg] and [of_cents] when the exact result does not
    fit in 64 bits. An overflow in ledger arithmetic is an invariant violation
    (the representable range is about ±9.2 trillion dollars), never an expected
    input error, so it is an exception rather than a [result]. {!Rpc} catches it
    at the protocol boundary so the process never dies. *)

val micro_per_dollar : int64
(** [1_000_000L]. *)

val micro_per_share : int64
(** [1_000_000L]: the quantity scale used by {!mul_qty}. *)

val zero : t

val of_micro : int64 -> t
(** Wrap a micro-dollar count as received from the protocol. Total. *)

val to_micro : t -> int64
(** Unwrap for serialization. [to_micro (of_micro n) = n]. *)

val of_cents : int -> t
(** [of_cents 12345] is $123.45. Raises [Overflow] if [cents * 10_000] does not
    fit in 64 bits. *)

val add : t -> t -> t
(** Exact sum. Raises [Overflow]. *)

val sub : t -> t -> t
(** Exact difference. Raises [Overflow]. *)

val neg : t -> t
(** Negation. Raises [Overflow] only for [of_micro Int64.min_int]. *)

val mul_qty : t -> qty_micro:int64 -> (t, [ `Overflow ]) result
(** [mul_qty price ~qty_micro] is the value of [qty_micro] micro-shares at
    [price] per share, in micro-dollars: [price * qty_micro / micro_per_share].

    The product is computed without intermediate 64-bit overflow by splitting
    the quantity into whole shares and the fractional micro-share remainder, so
    realistic inputs such as $5,000 × 10,000 shares (whose naive product is
    5×10^19) are exact. The fractional part truncates toward zero on the
    magnitude and the sign is applied afterwards, so [mul_qty p ~qty_micro:(-q)]
    equals [neg (mul_qty p ~qty_micro:q)]: a buy and a sell of the same quantity
    at the same price net to exactly zero.

    Returns [Error `Overflow] when the result does not fit in 64 bits. This can
    be triggered by protocol inputs, so it is a [result], not an exception. *)

val compare : t -> t -> int
val equal : t -> t -> bool

val to_string : t -> string
(** Decimal dollars with exactly six fractional digits and no thousands
    separator, e.g. ["-12.345678"], ["0.000000"]. Never exponent notation. *)

val pp : Format.formatter -> t -> unit
