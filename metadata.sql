CREATE TABLE public.res_partner (
	id serial4 NOT NULL,
	"name" varchar NULL, --Cliente, compañia, titular y lugar de recogida
	company_id int4 NULL,
	display_name varchar NULL,
	parent_id int4 NULL,
	"type" varchar NULL,
	street varchar NULL,
	street2 varchar NULL,
	zip varchar NULL,
	city varchar NULL,
	state_id int4 NULL,
	country_id int4 NULL,
	email varchar NULL, -- Email
	phone varchar NULL,
	mobile varchar NULL,
	industry_id int4 NULL,
);

CREATE TABLE public.pnt_agreement_agreement (
	id serial4 NOT NULL,
	"name" varchar NOT NULL, -- Contrato
	pnt_complete_name varchar NULL,
	active bool NULL,
	pnt_holder_id int4 NULL,
	pnt_partner_pickup_id int4 NULL,
	pnt_parent_agreement_id int4 NULL,
	state varchar NULL, --activo(active) o no
	
);

CREATE TABLE public.pnt_agreement_line (
	id serial4 NOT NULL,
	pnt_agreement_id int4 NOT NULL,
	display_type varchar NULL,
	pnt_product_id int4 NULL,
	pnt_product_economic_uom int4 NULL,
	pnt_price_unit numeric NOT NULL,
	pnt_container_id int4 NULL,
	pnt_monetary_waste varchar NULL,
	"name" text NOT NULL,
	company_id int4 NULL,
	pnt_product_waste_id int4 NULL,
);

CREATE TABLE public.product_product (
	id serial4 NOT NULL,
	message_main_attachment_id int4 NULL,
	default_code varchar NULL, -- Tipo de contenedor o residuo
	active bool NULL,
	product_tmpl_id int4 NOT NULL,
	volume numeric NULL,
	weight numeric NULL,
	is_dangerous bool NULL, -- Peligroso o no
);

CREATE TABLE public.product_template (
	id serial4 NOT NULL, -- Residuo o Contenedor
	message_main_attachment_id int4 NULL,
	"name" varchar NOT NULL, -- Nombre residuo o contenedor
	"sequence" int4 NULL,
	description text NULL,
	description_purchase text NULL,
	description_sale text NULL,
	"type" varchar NOT NULL,
	volume numeric NULL,
	weight numeric NULL,
	company_id int4 NULL,
	active bool NULL,
	color int4 NULL,
	default_code varchar NULL, -- Tipo contenedor
    );

    
CREATE TABLE public.product_category (
	id serial4 NOT NULL,
	"name" varchar NOT NULL,
	complete_name varchar NULL, -- tipo material o residuo(papel y carton, plastico, textil, sanitario)
	parent_id int4 NULL,
	code varchar NULL,
	"type" varchar NULL,
	pnt_is_sanitary bool NULL,
	pnt_is_container bool NULL,
	pnt_service bool NULL,
	pnt_order_budget_format varchar NULL,
);

-- para sacar toda la informacion con un mail de alguien: SELECT rp.name, paa.name, pt.name as producto, uu.name as UNIDAD_ECONOMICA, pal.pnt_price_unit as precio_unitario, ptContainer.name as ENVASE FROM public.pnt_agreement_agreement paa  left join res_partner rp on paa.pnt_holder_id = rp.id LEFT JOIN pnt_agreement_line pal ON paa.id  = pal.pnt_agreement_id left join uom_uom uu on pal.pnt_product_Economic_uom = uu.id LEFT JOIN product_product pp ON pal.pnt_product_id  = pp.id LEFT JOIN product_template pt ON pp.product_tmpl_id  = pt.id LEFT JOIN product_product ppContainer ON pal.pnt_container_id  = ppContainer.id LEFT JOIN product_template ptContainer ON ppContainer.product_tmpl_id  = ptContainer.id where pnt_holder_id IN (select id from res_partner where email ilike '%%' and is_company = true)
-- para sacar todos los lugares de recogida con un mail de alguien: SELECT paa.pnt_complete_name, rprecog.display_name as Lugares_de_recogida FROM public.pnt_agreement_agreement paa left join res_partner rp on paa.pnt_holder_id = rp.id left join pnt_agreement_partner_pickup_rel pappr on paa.id = pappr.pnt_agreement_id left join res_partner rprecog on pappr.partner_id = rprecog.id where paa.pnt_holder_id IN (select id from res_partner where email ilike '%%' and is_company = true) and paa.state = 'done'

pnt_single_document.id can be joined with pnt_single_document_line.pnt_single_document_id
pnt_single_document_line.pnt_product_id can be joined with product_product.id
pnt_single_document_line.pnt_container_id can be joined with product_product.id
product_template.id can be joined with product_category.product_tmpl_id
pnt_agreement_agreement.pnt_holder_id can be joined with res_partner.id
pnt_agreement_agreement.id can be joined with pnt_agreement_line.pnt_agreement_id
pnt_agreement_line.pnt_product_Economic_uom can be joined with uom_uom.id
pnt_agreement_line.pnt_product_id can be joined with product_product.id
product_product.product_tmpl_id can be joined with product_template.id
pnt_agreement_line.pnt_container_id can be joined with product_product.id
pnt_agreement_agreement.id can be joined with pnt_agreement_partner_pickup_rel.pnt_agreement_id
pnt_agreement_partner_pickup_rel.partner_id can be joined with res_partner.id