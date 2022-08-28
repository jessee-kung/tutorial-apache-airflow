USE airflow_demo_covid19;

CREATE TABLE IF NOT EXISTS `regional_based` (
    `id` int(11) NOT NULL auto_increment,
    `updated` date NOT NULL,
    `region` varchar(128) NOT NULL,
    `latitude` float(10,6) NOT NULL,
    `longitude` float(10,6) NOT NULL,
    `death` int(11) NOT NULL,
    `confirmed` int(11) NOT NULL,
    PRIMARY KEY(`id`),
    INDEX `idx_updated` (`updated`),
    INDEX `idx_death` (`death`),
    INDEX `idx_confirmed` (`confirmed`)
);

CREATE TABLE IF NOT EXISTS `country_based` (
    `id` int(11) NOT NULL auto_increment,
    `updated` date NOT NULL,
    `country` varchar(32) NOT NULL,
    `death` int(11) NOT NULL,
    `confirmed` int(11) NOT NULL,
    PRIMARY KEY(`id`),
    INDEX `idx_updated` (`updated`),
    INDEX `idx_death` (`death`),
    INDEX `idx_confirmed` (`confirmed`)
);