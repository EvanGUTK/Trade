type t = int64

exception Overflow

let micro_per_dollar = 1_000_000L
let micro_per_share = 1_000_000L
let zero = 0L
let of_micro n = n
let to_micro t = t
let nonneg a = Int64.compare a 0L >= 0

(* Checked [Int64] primitives. Each returns [None] instead of wrapping. *)

(* Overflow iff both operands have the same sign and the sum has the other. *)
let checked_add a b =
  let s = Int64.add a b in
  if nonneg a = nonneg b && nonneg s <> nonneg a then None else Some s

(* Overflow iff the operands have different signs and the difference does not
   have the sign of [a]. *)
let checked_sub a b =
  let d = Int64.sub a b in
  if nonneg a <> nonneg b && nonneg d <> nonneg a then None else Some d

let checked_neg a =
  if Int64.equal a Int64.min_int then None else Some (Int64.neg a)

let checked_abs a = if nonneg a then Some a else checked_neg a

let checked_mul a b =
  if Int64.equal a 0L || Int64.equal b 0L then Some 0L
  else if
    (Int64.equal a Int64.min_int && Int64.equal b (-1L))
    || (Int64.equal b Int64.min_int && Int64.equal a (-1L))
  then None
  else
    let p = Int64.mul a b in
    if Int64.equal (Int64.div p b) a then Some p else None

let or_raise = function Some v -> v | None -> raise Overflow
let add a b = or_raise (checked_add a b)
let sub a b = or_raise (checked_sub a b)
let neg a = or_raise (checked_neg a)
let of_cents cents = or_raise (checked_mul (Int64.of_int cents) 10_000L)

let mul_qty price ~qty_micro =
  let ( let* ) o f = match o with Some v -> f v | None -> Error `Overflow in
  let negative = nonneg price <> nonneg qty_micro in
  let* p = checked_abs price in
  let* q = checked_abs qty_micro in
  let whole_shares = Int64.div q micro_per_share in
  let frac_micro = Int64.rem q micro_per_share in
  let* whole_value = checked_mul p whole_shares in
  let* frac_numerator = checked_mul p frac_micro in
  let frac_value = Int64.div frac_numerator micro_per_share in
  let* total = checked_add whole_value frac_value in
  (* [total >= 0], so negation cannot overflow. *)
  Ok (if negative then Int64.neg total else total)

let compare = Int64.compare
let equal = Int64.equal

let to_string t =
  let negative = Int64.compare t 0L < 0 in
  (* The magnitude is handled as unsigned so that [Int64.min_int] prints. *)
  let magnitude = if negative then Int64.neg t else t in
  let whole = Int64.unsigned_div magnitude micro_per_dollar in
  let frac = Int64.unsigned_rem magnitude micro_per_dollar in
  Printf.sprintf "%s%Lu.%06Lu" (if negative then "-" else "") whole frac

let pp fmt t = Format.pp_print_string fmt (to_string t)
